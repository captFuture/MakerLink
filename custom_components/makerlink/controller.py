"""Business logic of a MakerLink unit (no Home Assistant imports).

MachineController is a port of docs/legacy/maker-reader-logic.yaml; the reader
itself only delivers card scans, shows two text lines and switches power.
Timers are driven by tick(), which the hub calls once per second.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from .const import (
    CARD_COOLDOWN,
    DEFAULT_MIN_BALANCE,
    DEFAULT_PULSE_TIME,
    DEFAULT_SHUTDOWN_TIME,
    DOOR_LOG_DELAY,
    EVENT_CARD_REJECTED,
    EVENT_DOOR_ACCESS,
    EVENT_SESSION_STARTED,
    EVENT_SESSION_STOPPED,
    KIND_DOOR,
    KIND_MACHINE,
    MESSAGE_TIME,
    STOP_SCREEN_TIME,
)
from .display import View, render
from .mars_format import DoorResult, MarsError, MarsResult, uid_to_mars

_LOGGER = logging.getLogger(__name__)

PENDING_RETRY_TICKS = 60

STATUS_IDLE = "idle"
STATUS_CHECKING = "checking"
STATUS_ACTIVE = "active"
STATUS_STOPPING = "stopping"
STATUS_COOLDOWN = "cooldown"
STATUS_ADMIN = "admin"
STATUS_OUT_OF_ORDER = "out_of_order"
STATUS_MESSAGE = "message"
STATUS_INTERLOCK_OPEN = "interlock_open"
STATUSES = [
    STATUS_IDLE,
    STATUS_CHECKING,
    STATUS_ACTIVE,
    STATUS_STOPPING,
    STATUS_COOLDOWN,
    STATUS_ADMIN,
    STATUS_OUT_OF_ORDER,
    STATUS_MESSAGE,
    STATUS_INTERLOCK_OPEN,
]


class MarsApi(Protocol):
    """Backend operations a controller needs (implemented by api.MarsApiClient)."""

    async def start(
        self, rfid: str, unit_id: int, machine_type: str, min_balance: float
    ) -> MarsResult: ...

    async def stop(
        self, key: int, unit_id: int, machine_type: str, end: int | None = None
    ) -> MarsResult: ...

    async def door_check(self, rfid: str) -> DoorResult: ...

    async def log_door(self, rfid: str, allowed: bool, unit_id: int) -> None: ...


class Hardware(Protocol):
    """Reader/actuator side (implemented by hub.HassHardware)."""

    def power_state(self) -> bool | None:
        """Current state of the power target, None if unavailable."""

    async def set_power(self, on: bool) -> None: ...

    def interlock_closed(self) -> bool:
        """True if all configured interlock switches are closed (or none exist)."""

    async def show(self, line1: str, line2: str) -> None: ...


EventCallback = Callable[[str, dict[str, Any]], None]


class UnitController:
    """Shared parts of machine and door controllers."""

    kind: str

    def __init__(
        self,
        *,
        name: str,
        unit_id: int,
        api: MarsApi,
        hardware: Hardware,
        settings: dict[str, Any] | None = None,
        fire_event: EventCallback | None = None,
        save: Callable[[], None] | None = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.name = name
        self.unit_id = unit_id
        self.api = api
        self.hw = hardware
        self.settings: dict[str, Any] = {"out_of_order": False, **(settings or {})}
        self._fire = fire_event or (lambda _event, _data: None)
        self._save = save or (lambda: None)
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[], None]] = []
        self._last_lines: tuple[str, str] | None = None
        self._last_fingerprint: tuple | None = None

        self.card_cooldown = 0
        self.message: tuple[str, str] | None = None
        self.message_timer = 0
        self.busy = ""
        self.last_user = ""

    # ----- listeners / persistence -------------------------------------------------

    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def _notify(self) -> None:
        fingerprint = self._fingerprint()
        if fingerprint == self._last_fingerprint:
            return
        self._last_fingerprint = fingerprint
        for cb in list(self._listeners):
            cb()

    def _fingerprint(self) -> tuple:
        return (
            self.status,
            self.last_user,
            self._last_lines,
            tuple(sorted(self.settings.items())),
        )

    def as_store(self) -> dict[str, Any]:
        """State to persist across restarts."""
        return {"settings": dict(self.settings)}

    @property
    def out_of_order(self) -> bool:
        return bool(self.settings.get("out_of_order"))

    async def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self._save()
        await self._refresh()

    # ----- inputs ------------------------------------------------------------------

    async def on_card(self, raw_uid: str) -> None:
        """A card was presented at the reader."""
        rfid = uid_to_mars(raw_uid)
        if rfid is None:
            _LOGGER.debug("%s: ignoring non-UID tag %r", self.name, raw_uid)
            return
        if self.card_cooldown > 0:
            _LOGGER.debug("%s: card ignored, cooldown %ss", self.name, self.card_cooldown)
            return
        self.card_cooldown = CARD_COOLDOWN
        async with self._lock:
            if self.out_of_order:
                self._reject(rfid, "Ausser Betrieb", ("AUSSER BETRIEB", "Bitte warten"))
            else:
                await self._handle_card(rfid)
        await self._refresh()

    async def tick(self) -> None:
        """Advance timers by one second."""
        if self.card_cooldown > 0:
            self.card_cooldown -= 1
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = None
        await self._tick()
        await self._refresh()

    async def on_power_changed(self, is_on: bool | None) -> None:
        """The power target changed state."""

    async def on_interlock_changed(self) -> None:
        """An interlock switch changed state."""
        await self._refresh()

    # ----- helpers -----------------------------------------------------------------

    async def _handle_card(self, rfid: str) -> None:
        raise NotImplementedError

    async def _tick(self) -> None:
        pass

    def _view(self) -> View:
        raise NotImplementedError

    @property
    def status(self) -> str:
        raise NotImplementedError

    def _show_message(self, line1: str, line2: str = "", seconds: int = MESSAGE_TIME) -> None:
        self.message = (line1, line2)
        self.message_timer = seconds

    def _reject(self, rfid: str, reason: str, lines: tuple[str, str] | None = None) -> None:
        _LOGGER.info("%s: card rejected: %s", self.name, reason)
        self._show_message(*(lines or ("ABGELEHNT", reason)))
        self._fire(
            EVENT_CARD_REJECTED,
            {"unit": self.name, "unit_id": self.unit_id, "reason": reason},
        )

    async def _refresh(self) -> None:
        lines = render(self._view())
        if lines != self._last_lines:
            self._last_lines = lines
            try:
                await self.hw.show(*lines)
            except Exception:
                _LOGGER.debug("%s: display update failed", self.name, exc_info=True)
        self._notify()

    @property
    def display_lines(self) -> tuple[str, str] | None:
        return self._last_lines


class MachineController(UnitController):
    """Card on = power on + session start, card again = stop + billing + cooldown."""

    kind = KIND_MACHINE

    def __init__(self, *, machine_type: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings.setdefault("machine_type", machine_type)
        self.settings.setdefault("min_balance", DEFAULT_MIN_BALANCE)
        self.settings.setdefault("shutdown_time", DEFAULT_SHUTDOWN_TIME)
        self.settings.setdefault("admin", False)

        self.session_key: int | None = None
        self.session_start: float | None = None
        self.shutdown_counter = 0
        self.stop_screen = 0
        self.stop_title = "Schaltet aus"
        self.last_cost: float | None = None
        self.last_balance: float | None = None
        self.pending_stops: list[dict[str, Any]] = []
        self._pending_timer = 0
        # Power state we caused ourselves; None = not yet known (startup).
        self._expected_power: bool | None = None

    # ----- persistence -------------------------------------------------------------

    def as_store(self) -> dict[str, Any]:
        return {
            **super().as_store(),
            "session_key": self.session_key,
            "session_start": self.session_start,
            "user": self.last_user,
            "pending_stops": list(self.pending_stops),
        }

    def restore(self, data: dict[str, Any]) -> None:
        """Restore persisted state; reconciled once the power state is known."""
        self.settings.update(data.get("settings") or {})
        self.session_key = data.get("session_key")
        self.session_start = data.get("session_start")
        self.last_user = data.get("user") or ""
        self.pending_stops = list(data.get("pending_stops") or [])
        # Admin mode does not survive a restart.
        self.settings["admin"] = False

    async def async_start(self) -> None:
        """Reconcile with the current power state after setup."""
        await self.on_power_changed(self.hw.power_state())
        await self._refresh()

    # ----- properties --------------------------------------------------------------

    @property
    def machine_type(self) -> str:
        return self.settings["machine_type"]

    @property
    def admin(self) -> bool:
        return bool(self.settings.get("admin"))

    @property
    def session_active(self) -> bool:
        return self.session_key is not None

    @property
    def status(self) -> str:
        if self.out_of_order:
            return STATUS_OUT_OF_ORDER
        if self.admin:
            return STATUS_ADMIN
        if self.busy:
            return STATUS_CHECKING if self.busy.startswith("Pruefe") else STATUS_STOPPING
        if self.session_active:
            return STATUS_ACTIVE
        if self.shutdown_counter > 0:
            return STATUS_COOLDOWN
        if self.message:
            return STATUS_MESSAGE
        if not self.hw.interlock_closed():
            return STATUS_INTERLOCK_OPEN
        return STATUS_IDLE

    def _fingerprint(self) -> tuple:
        return (
            *super()._fingerprint(),
            self.session_key,
            self.last_cost,
            self.last_balance,
            len(self.pending_stops),
        )

    def _view(self) -> View:
        return View(
            kind=self.kind,
            out_of_order=self.out_of_order,
            admin=self.admin,
            busy=self.busy,
            message=self.message,
            shutdown_counter=self.shutdown_counter,
            user_name=self.last_user,
            session_active=self.session_active,
            stop_screen=self.stop_screen,
            stop_title=self.stop_title,
            balance=self.last_balance,
            interlock_open=not self.hw.interlock_closed(),
        )

    # ----- power -------------------------------------------------------------------

    async def _set_power(self, on: bool) -> None:
        self._expected_power = on
        await self.hw.set_power(on)

    # ----- card --------------------------------------------------------------------

    async def _handle_card(self, rfid: str) -> None:
        if self.admin:
            # A member card ends maintenance mode; the session decides about power.
            self.settings["admin"] = False
        if self.session_active:
            await self._stop("card")
        else:
            await self._start(rfid)

    async def _start(self, rfid: str) -> None:
        if not self.hw.interlock_closed():
            self._reject(rfid, "Tuer offen", ("TUER OFFEN", "Bitte schliessen"))
            await self._power_off_if_idle()
            return
        if self.hw.power_state() is None:
            self._reject(rfid, "Schaltziel offline", ("FEHLER", "Schalter offline"))
            return

        self.busy = "Pruefe..."
        await self._refresh()
        try:
            res = await self.api.start(
                rfid, self.unit_id, self.machine_type, float(self.settings["min_balance"])
            )
        except MarsError as err:
            _LOGGER.warning("%s: start failed: %s", self.name, err)
            self.busy = ""
            self._reject(rfid, str(err), ("FEHLER", err.display))
            await self._power_off_if_idle()
            return
        self.busy = ""

        if res.ok and res.key is not None:
            self.session_key = res.key
            self.session_start = self._clock()
            self.last_user = res.name or ""
            self.shutdown_counter = 0
            self.message = None
            await self._set_power(True)
            self._save()
            self._fire(
                EVENT_SESSION_STARTED,
                {
                    "unit": self.name,
                    "unit_id": self.unit_id,
                    "key": res.key,
                    "user": self.last_user,
                    "machine_type": self.machine_type,
                },
            )
        elif res.ok:
            # Booked without a session (e.g. coffee machine, unit 6).
            self.last_user = res.name or ""
            self.last_cost = res.cost
            self.last_balance = res.balance
            self.stop_title = res.msg or "Verrechnet"
            self.stop_screen = STOP_SCREEN_TIME
        else:
            self._reject(rfid, res.msg or "Abgelehnt", ("ABGELEHNT", res.msg or "Abgelehnt"))
            await self._power_off_if_idle()

    async def _power_off_if_idle(self) -> None:
        if not self.session_active and self.shutdown_counter == 0 and self.hw.power_state():
            await self._set_power(False)

    # ----- stop --------------------------------------------------------------------

    async def stop_session(self, reason: str = "manual") -> None:
        """Stop the running session (button/service)."""
        async with self._lock:
            if self.session_active:
                await self._stop(reason)
            elif self.shutdown_counter > 0:
                self.shutdown_counter = 0
                await self._set_power(False)
            elif self.admin:
                await self.set_admin(False)
        await self._refresh()

    async def _stop(self, reason: str, immediate: bool = False) -> None:
        key = self.session_key
        assert key is not None
        end = int(self._clock())
        self.busy = "Stop..."
        await self._refresh()
        res: MarsResult | None
        try:
            res = await self.api.stop(key, self.unit_id, self.machine_type)
        except MarsError as err:
            _LOGGER.warning("%s: stop of session %s failed, queued: %s", self.name, key, err)
            self.pending_stops.append(
                {"key": key, "unit_id": self.unit_id, "type": self.machine_type, "end": end}
            )
            res = None
        else:
            if not res.ok:
                _LOGGER.warning("%s: backend refused stop of %s: %s", self.name, key, res.msg)
        self.busy = ""

        duration = int(end - self.session_start) if self.session_start else None
        self.session_key = None
        self.session_start = None
        self.settings["admin"] = False
        self.last_cost = res.cost if res else None
        self.last_balance = res.balance if res else None
        self.stop_title = "Schaltet aus"
        self.stop_screen = STOP_SCREEN_TIME
        if res is None:
            self._show_message("Server offline", "Wird nachgebucht")

        shutdown = int(self.settings["shutdown_time"])
        if immediate or shutdown <= 0:
            self.shutdown_counter = 0
            await self._set_power(False)
        else:
            self.shutdown_counter = shutdown
            if not self.hw.power_state():
                # Keep cooling (legacy: relay goes back on after an external off).
                await self._set_power(True)
        self._save()
        self._fire(
            EVENT_SESSION_STOPPED,
            {
                "unit": self.name,
                "unit_id": self.unit_id,
                "key": key,
                "user": self.last_user,
                "reason": reason,
                "cost": self.last_cost,
                "balance": self.last_balance,
                "duration_s": duration,
                "billed": res is not None and res.ok,
            },
        )

    async def retry_pending(self) -> None:
        """Try to book stops that failed while the backend was unreachable."""
        remaining = []
        for item in self.pending_stops:
            try:
                res = await self.api.stop(item["key"], item["unit_id"], item["type"], item["end"])
            except MarsError:
                remaining.append(item)
                continue
            _LOGGER.info("%s: queued stop %s booked: %s", self.name, item["key"], res.msg)
        if len(remaining) != len(self.pending_stops):
            self.pending_stops = remaining
            self._save()

    # ----- admin -------------------------------------------------------------------

    async def set_admin(self, on: bool) -> None:
        """Maintenance mode: power on without a session."""
        if on:
            if self.session_active:
                return
            if not self.hw.interlock_closed():
                self._show_message("TUER OFFEN", "Bitte schliessen")
                await self._refresh()
                return
            self.settings["admin"] = True
            self.shutdown_counter = 0
            await self._set_power(True)
        else:
            self.settings["admin"] = False
            if not self.session_active and self.shutdown_counter == 0:
                await self._set_power(False)
        await self._refresh()

    # ----- external events ---------------------------------------------------------

    async def on_power_changed(self, is_on: bool | None) -> None:
        if is_on is None:
            await self._refresh()
            return
        if self._expected_power is None:
            # First known state after startup: reconcile a restored session.
            self._expected_power = is_on
            if self.session_active and not is_on:
                _LOGGER.info("%s: power off after restart, closing session", self.name)
                async with self._lock:
                    await self._stop("restart", immediate=True)
            await self._refresh()
            return
        if is_on == self._expected_power:
            return
        self._expected_power = is_on
        async with self._lock:
            if is_on:
                if not self.session_active and self.shutdown_counter == 0:
                    if not self.hw.interlock_closed():
                        await self._set_power(False)
                    else:
                        _LOGGER.info("%s: switched on externally -> admin mode", self.name)
                        self.settings["admin"] = True
            elif self.admin:
                self.settings["admin"] = False
            elif self.shutdown_counter > 0:
                self.shutdown_counter = 0
            elif self.session_active:
                _LOGGER.info("%s: switched off externally -> stop session", self.name)
                await self._stop("power_off")
        await self._refresh()

    async def on_interlock_changed(self) -> None:
        if not self.hw.interlock_closed():
            async with self._lock:
                if self.session_active:
                    _LOGGER.info("%s: interlock opened -> immediate stop", self.name)
                    await self._stop("interlock", immediate=True)
                elif self.shutdown_counter > 0 or self.admin:
                    self.shutdown_counter = 0
                    self.settings["admin"] = False
                    await self._set_power(False)
        await self._refresh()

    async def _tick(self) -> None:
        if self.stop_screen > 0:
            self.stop_screen -= 1
        if self.shutdown_counter > 0:
            self.shutdown_counter -= 1
            if self.shutdown_counter == 0:
                _LOGGER.debug("%s: cooldown done -> power off", self.name)
                await self._set_power(False)
        if self.pending_stops:
            self._pending_timer += 1
            if self._pending_timer >= PENDING_RETRY_TICKS:
                self._pending_timer = 0
                await self.retry_pending()


class DoorController(UnitController):
    """Card -> doorLockCheck -> short relay pulse -> logDoorAccess."""

    kind = KIND_DOOR

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings.setdefault("pulse_time", DEFAULT_PULSE_TIME)
        self.last_allowed: bool | None = None
        self._log_tasks: set[asyncio.Task] = set()

    @property
    def status(self) -> str:
        if self.out_of_order:
            return STATUS_OUT_OF_ORDER
        if self.busy:
            return STATUS_CHECKING
        if self.message:
            return STATUS_MESSAGE
        return STATUS_IDLE

    def _view(self) -> View:
        return View(
            kind=self.kind,
            out_of_order=self.out_of_order,
            busy=self.busy,
            message=self.message,
        )

    async def async_start(self) -> None:
        await self._refresh()

    async def open_door(self) -> None:
        """Open without a card (button/service)."""
        async with self._lock:
            await self._pulse()

    async def _handle_card(self, rfid: str) -> None:
        self.busy = "Pruefe..."
        await self._refresh()
        try:
            res = await self.api.door_check(rfid)
        except MarsError as err:
            self.busy = ""
            self._reject(rfid, str(err), ("FEHLER", err.display))
            return
        self.busy = ""
        self.last_allowed = res.allowed
        self._fire(
            EVENT_DOOR_ACCESS,
            {
                "unit": self.name,
                "unit_id": self.unit_id,
                "allowed": res.allowed,
                "reason": res.reason,
            },
        )
        if res.allowed:
            self._show_message("WILLKOMMEN", res.reason, seconds=max(MESSAGE_TIME, 1))
            await self._refresh()
            self._schedule_log(rfid, True)
            await self._pulse()
        else:
            self._reject(rfid, res.reason, ("KEIN ZUTRITT", res.reason))
            self._schedule_log(rfid, False)

    async def _pulse(self) -> None:
        await self.hw.set_power(True)
        try:
            await self._sleep(float(self.settings["pulse_time"]))
        finally:
            await self.hw.set_power(False)

    def _schedule_log(self, rfid: str, allowed: bool) -> None:
        async def _log() -> None:
            await self._sleep(DOOR_LOG_DELAY)
            try:
                await self.api.log_door(rfid, allowed, self.unit_id)
            except MarsError as err:
                _LOGGER.warning("%s: logDoorAccess failed: %s", self.name, err)

        task = asyncio.ensure_future(_log())
        self._log_tasks.add(task)
        task.add_done_callback(self._log_tasks.discard)
