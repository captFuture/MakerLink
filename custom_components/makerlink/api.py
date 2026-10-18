"""HTTP client for the MARS backend (machineswitch.php), see docs/API.md."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .mars_format import (
    DoorResult,
    MarsAuthError,
    MarsConnectionError,
    MarsHttpError,
    MarsResult,
    parse_body,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=8)


class MarsApiClient:
    """Thin async wrapper around the GET endpoints."""

    def __init__(
        self, session: aiohttp.ClientSession, url: str, api_key: str, verify_ssl: bool = True
    ) -> None:
        self._session = session
        self._url = url
        self._headers = {"X-MARS-Key": api_key, "User-Agent": "HomeAssistant/MakerLink"}
        self._ssl = None if verify_ssl else False

    async def _get(self, params: dict[str, Any], ok_status: tuple[int, ...] = (200,)) -> Any:
        params = {k: str(v) for k, v in params.items() if v is not None}
        try:
            async with self._session.get(
                self._url, params=params, headers=self._headers, timeout=TIMEOUT, ssl=self._ssl
            ) as resp:
                body = await resp.text()
                status = resp.status
        except (TimeoutError, aiohttp.ClientError) as err:
            raise MarsConnectionError(str(err) or type(err).__name__) from err

        _LOGGER.debug("MARS %s -> %s %s", params.get("action"), status, body[:200])
        data = parse_body(body)
        if status == 401:
            raise MarsAuthError("Unauthorized")
        if status not in ok_status:
            msg = data.get("msg", "") if isinstance(data, dict) else body[:100]
            raise MarsHttpError(status, msg)
        return data

    async def validate(self) -> None:
        """Check URL, key and DB: a request without action must answer 400."""
        await self._get({}, ok_status=(400,))

    async def start(
        self, rfid: str, unit_id: int, machine_type: str, min_balance: float
    ) -> MarsResult:
        data = await self._get(
            {
                "action": "start",
                "rfid": rfid,
                "unitid": unit_id,
                "type": machine_type,
                "min_balance": min_balance,
            }
        )
        return MarsResult.from_json(data)

    async def stop(
        self, key: int, unit_id: int, machine_type: str, end: int | None = None
    ) -> MarsResult:
        data = await self._get(
            {"action": "stop", "key": key, "unitid": unit_id, "type": machine_type, "end": end}
        )
        return MarsResult.from_json(data)

    async def door_check(self, rfid: str) -> DoorResult:
        data = await self._get({"action": "doorLockCheck", "rfid": rfid})
        return DoorResult.from_json(data)

    async def log_door(self, rfid: str, allowed: bool, unit_id: int) -> None:
        await self._get(
            {
                "action": "logDoorAccess",
                "rfid": rfid,
                "status": "TRUE" if allowed else "FALSE",
                "unitid": unit_id,
                "check": 2,
            }
        )
