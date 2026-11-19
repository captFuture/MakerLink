#!/usr/bin/env python3
"""Mock des MARS-Backends (backend/machineswitch.php) mit Test-GUI.

Reine Standardbibliothek. Start:  python tools/mock_server/server.py [--port 8080]

- API:  http://<host>:<port>/machineswitch.php   (Header X-MARS-Key)
- GUI:  http://<host>:<port>/

Die Logik ist 1:1 aus machineswitch.php nachgebaut (Abrechnung, Idempotenz, Statuscodes),
die Datenbank ist ein In-Memory-Zustand, der in der GUI bearbeitet werden kann.
Zusaetzlich gibt es Fehlerinjektion (Ausfall, Timeout, kaputte Antworten, verlorene
Antworten) und eine verschiebbare Serverzeit.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import threading
import time
from collections import deque
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).parent
LOCK = threading.RLock()
REQUEST_LOG: deque = deque(maxlen=300)

UNLIMITED_PIDS = {12, 13, 14, 15, 16, 19, 20, 50, 51, 52}  # getPlanVomUser
WHITELIST_PIDS = UNLIMITED_PIDS | {53}  # action=whitelist
STANDARD_PIDS = {3, 17, 22}
BASIC_PID = 2
TYPES = ("machine", "laser", "3dprint", "dtf", "kiln")
PRICE_COLS = {"laser": "laser_full", "3dprint": "3dprint_min", "dtf": "dtf_drucker_min"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# --------------------------------------------------------------------------- State
STATE: dict = {}


def now_ts() -> float:
    return time.time() + STATE["config"].get("time_offset_s", 0)


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def seed_state() -> dict:
    """Beispielszenario: ein Mitglied pro interessantem Sonderfall."""
    now = int(time.time())

    def m(cid, first, last, cards, memberships, units, balance=0.0, blocked=False, deleted=False):
        return {
            "cid": cid, "firstName": first, "lastName": last,
            "cards": [{"serial": c, "expired": False} for c in cards],
            "memberships": [{"pid": p, "name": n} for p, n in memberships],
            "trained": units, "blocked": blocked, "deleted": deleted,
            "_balance": balance,
        }

    members = [
        m(1, "Max", "Unlimited", ["0xf4 0x96 0xd2 0x28"], [(12, "Unlimited")], [1720, 1721, 1722, 1730, 9998], 50.0),
        m(2, "Erika", "Basic", ["0x1 0x2 0x3 0x4"], [(2, "Basic")], [1720, 1721, 1730], 20.0),
        m(3, "Sepp", "Standard", ["0x5 0x6 0x7 0x8"], [(3, "Standard")], [1720, 1721, 1722, 1730], 12.3),
        m(4, "Leo", "Leer", ["0x9 0xa 0xb 0xc"], [(2, "Basic")], [1720, 1721, 1730], 0.0),
        m(5, "Bernd", "Blockiert", ["0xd 0xe 0xf 0x10"], [(12, "Unlimited")], [1720, 1730], 30.0, blocked=True),
        m(6, "Hanna", "Ohne-Schulung", ["0x11 0x12 0x13 0x14"], [(2, "Basic")], [], 30.0),
        m(7, "Lisa", "Limited", ["0x15 0x16 0x17 0x18"],
          [(2, "Mon 1822"), (2, "Wed 1822")], [1720, 1730], 15.0),
    ]
    state = {
        "config": {"api_key": "test-key", "latency_ms": 0, "time_offset_s": 0},
        "prices": {
            "1": {"laser_full": 2.5, "3dprint_min": 0.1, "dtf_drucker_min": 0.2},
            "2": {"laser_full": 2.0, "3dprint_min": 0.08, "dtf_drucker_min": 0.15},
            "4": {"laser_full": 0.0, "3dprint_min": 0.0, "dtf_drucker_min": 0.0},
        },
        "units": [
            {"unitid": 1, "name": "Tuer aussen", "type": "door"},
            {"unitid": 6, "name": "Kaffeemaschine", "type": "coffee"},
            {"unitid": 1720, "name": "Laser", "type": "laser"},
            {"unitid": 1721, "name": "3D-Drucker", "type": "3dprint"},
            {"unitid": 1722, "name": "Brennofen", "type": "kiln"},
            {"unitid": 1730, "name": "Standmaschine", "type": "machine"},
        ],
        "members": members,
        "faults": [],
        "machine_time": [],
        "ledger": [],
        "access_log": [],
        "next_id": {"machine_time": 1000, "fault": 1},
    }
    for mem in state["members"]:
        bal = mem.pop("_balance")
        state["ledger"].append(
            {"ts": fmt_ts(now), "cid": mem["cid"], "fname": mem["firstName"],
             "lname": mem["lastName"], "payload": bal, "unitid": 0, "amount": bal}
        )
    return state


STATE = seed_state()


# --------------------------------------------------------------------------- PHP helpers
def intval(v) -> int:
    m = re.match(r"\s*[+-]?\d+", str(v or ""))
    return int(m.group()) if m else 0


def floatval(v, default=0.0) -> float:
    if v is None or v == "":
        return default
    m = re.match(r"\s*[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?", str(v))
    return float(m.group()) if m else 0.0


def php_round1(x: float) -> float:
    """round($x, 1, PHP_ROUND_HALF_UP)."""
    return float(Decimal(repr(float(x))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


class Exit(Exception):
    """Entspricht exit(json_encode(...)) in PHP."""

    def __init__(self, status: int, body):
        self.status, self.body = status, body


def json_out(ok, key, name, msg, status=200, **extra):
    raise Exit(status, {"ok": ok, "key": key, "name": name, "msg": msg, **extra})


# --------------------------------------------------------------------------- "DB"
def find_members(serial: str):
    s = serial.lower()
    return [m for m in STATE["members"] if any(c["serial"].lower() == s for c in m["cards"])]


def card_active(member, serial: str) -> bool:
    s = serial.lower()
    return any(c["serial"].lower() == s and not c["expired"] for c in member["cards"])


def current_payload(cid: int) -> dict:
    rows = [r for r in STATE["ledger"] if r["cid"] == cid]
    return rows[-1] if rows else {"payload": 0, "fname": "", "lname": ""}


def write_payload(m, new_payload, unitid, amount):
    row = current_payload(m["cid"])
    STATE["ledger"].append(
        {"ts": fmt_ts(now_ts()), "cid": m["cid"], "fname": row["fname"], "lname": row["lname"],
         "payload": new_payload, "unitid": unitid, "amount": amount}
    )


def plan_of_user(m) -> int:
    pids = {ms["pid"] for ms in m["memberships"]}
    if pids & UNLIMITED_PIDS:
        return 4
    if pids & STANDARD_PIDS:
        return 2
    return 1


def member_by_cid(cid):
    return next((m for m in STATE["members"] if m["cid"] == cid), None)


# --------------------------------------------------------------------------- Actions
def door_lock_check(rfid: str):
    rows = []  # (member, plan name) je Karte x Mitgliedschaft
    for m in find_members(rfid):
        if card_active(m, rfid):
            for ms in m["memberships"]:
                rows.append((m, ms["name"]))
    if not rows:
        return ["False", f"KEY {rfid} not in DB or enddate set"]
    if any(m["blocked"] or m["deleted"] for m, _ in rows):
        return ["False", "Mitglied ist blockiert oder geloescht"]
    plans = [n for _, n in rows]
    now = datetime.fromtimestamp(now_ts())
    today, hour = DAYS[now.weekday()], now.hour
    day_start = day_end = None
    for name in plans:
        if name[:3] == "Unl":
            return ["True", "Super User", name]
        if name[:3] != today:
            continue
        st, en = name[4:6], name[6:8]
        if not (st.isdigit() and en.isdigit()):
            continue
        day_start = int(st) if day_start is None else min(day_start, int(st))
        day_end = int(en) if day_end is None else max(day_end, int(en))
    if day_start is None:
        return ["False", "Wrong Day", "-".join(plans)]
    if hour < day_start or hour >= day_end:
        return ["False", "Wrong Time", "-".join(plans)]
    return ["True", "Limited User", "-".join(plans)]


def whitelist_serials() -> list:
    out = []
    for m in STATE["members"]:
        if m["deleted"] or m["blocked"]:
            continue
        if not any(ms["pid"] in WHITELIST_PIDS for ms in m["memberships"]):
            continue
        for c in m["cards"]:
            if not c["expired"] and c["serial"] and c["serial"] not in out:
                out.append(c["serial"])
    return out


def log_door_access(rfid, status, unitid, t):
    cid = 0
    for m in find_members(rfid):
        if m["memberships"]:
            cid = m["cid"]
            break
    ts = t if (t and 0 < t < time.time()) else now_ts()
    STATE["access_log"].append(
        {"ts": fmt_ts(ts), "cid": cid, "rfid": rfid, "status": 1 if status == "TRUE" else 0,
         "unitid": unitid, "check": 2}
    )


def finish_session(row, just_closed: bool, mtype: str, unitid: int):
    if not just_closed and (mtype == "machine" or row["paid"] == 1):
        json_out(True, None, None, "Bereits gestoppt", already_stopped=True)
    m = member_by_cid(row["cid"])
    duration = (row["machine_end"] or 0) - row["machine_start"]
    if mtype == "machine":
        json_out(True, None, None, "Gestoppt", cost=0.0, duration_s=duration)

    if mtype == "kiln":
        cost, use = 40.0, 1
    else:
        col = PRICE_COLS[mtype]
        use = math.ceil(duration / 3600 * 4) if mtype == "laser" else math.ceil(duration / 60)
        price = STATE["prices"].get(str(plan_of_user(m)), {}) if m else {}
        cost = float(price.get(col, 0) or 0)
    old = float(current_payload(row["cid"])["payload"])
    amount = php_round1(-(cost * use))
    new = php_round1(old + amount)
    write_payload(m or {"cid": row["cid"]}, new, unitid, amount)
    row["paid"] = 1
    json_out(True, None, None, "Gestoppt", cost=amount, balance=new, duration_s=duration, use_units=use)


def handle_api(q: dict, headers) -> tuple:
    cfg = STATE["config"]
    valid = cfg["api_key"]
    if valid == "" or valid == "CHANGEME":
        return 500, {"ok": False, "msg": "Server nicht konfiguriert (API-Key fehlt)"}
    req_key = headers.get("X-MARS-Key", "")
    if req_key == "" or req_key != valid:
        return 401, {"ok": False, "msg": "Unauthorized"}
    try:
        _dispatch(q)
    except Exit as e:
        return e.status, e.body
    return 500, {"ok": False, "msg": "Mock: kein Exit"}


def _dispatch(q: dict):
    g = lambda k, d="": (q.get(k) or [d])[0]  # noqa: E731
    action = g("action").strip()
    rfid = g("rfid").strip()
    unitid = intval(g("unitid"))
    key = intval(g("key"))
    mtype = g("type", "machine").strip()
    min_bal = floatval(g("min_balance"), 5.0)

    if action == "doorLockCheck":
        if rfid == "":
            json_out(False, None, None, "Parameter rfid fehlt", 400)
        raise Exit(200, door_lock_check(rfid))
    if action == "logDoorAccess":
        status = g("status").strip().upper()
        check = intval(g("check"))
        if rfid == "":
            json_out(False, None, None, "Parameter rfid fehlt", 400)
        if unitid <= 0 or check != 2 or status not in ("TRUE", "FALSE"):
            json_out(False, None, None, "Ungueltige Parameter fuer Tuer (unitid>0, check=2, status=TRUE|FALSE)", 400)
        t = intval(g("time"))
        log_door_access(rfid, status, unitid, t if t > 0 else None)
        json_out(True, None, None, "Zutritt protokolliert", status=status, unitid=unitid)
    if action == "whitelist":
        cards = whitelist_serials()
        json_out(True, None, None, "Whitelist", cards=cards, count=len(cards))

    if action not in ("start", "stop", "offlineSession"):
        json_out(False, None, None, "Parameter action fehlt oder ungueltig (start|stop)", 400)
    if unitid <= 0:
        json_out(False, None, None, "Parameter unitid fehlt oder ungueltig", 400)
    if mtype not in TYPES:
        json_out(False, None, None, "Parameter type ungueltig (machine|laser|3dprint|dtf|kiln)", 400)
    if action in ("offlineSession", "start") and not rfid:
        json_out(False, None, None, "Parameter rfid fehlt", 400)
    if action == "stop" and key <= 0:
        json_out(False, None, None, "Parameter key fehlt oder ungueltig", 400)

    if action == "start":
        member = next((m for m in find_members(rfid) if m["memberships"]), None)
        if not member:
            json_out(False, None, None, "Karte unbekannt oder kein aktives Mitglied")
        name = member["firstName"]
        if member["deleted"]:
            json_out(False, None, name, "Zugang gesperrt (geloescht)")
        if member["blocked"]:
            json_out(False, None, name, "Zugang gesperrt (blockiert)")
        row = current_payload(member["cid"])
        balance = float(row["payload"])
        if unitid == 6:
            amount = -0.5
            new = php_round1(balance + amount)
            write_payload(member, new, unitid, amount)
            json_out(True, None, name, "Kaffee verrechnet", cost=amount, balance=new)
        if balance <= 0 and mtype != "machine":
            json_out(False, None, name, "Guthaben %.2f EUR reicht nicht (min %.2f EUR)" % (balance, min_bal))
        if balance < min_bal:
            json_out(False, None, name, "Guthaben %.2f EUR (min %.2f EUR)" % (balance, min_bal))
        if unitid not in member["trained"]:
            json_out(False, None, name, "Keine Schulung fuer diese Maschine")
        STATE["next_id"]["machine_time"] += 1
        new_id = STATE["next_id"]["machine_time"]
        STATE["machine_time"].append(
            {"id": new_id, "cid": member["cid"], "unitid": unitid, "fname": member["firstName"],
             "lname": member["lastName"], "machine_start": int(now_ts()), "machine_end": None, "paid": None}
        )
        json_out(True, new_id, name, "Aktiviert")

    if action == "stop":
        now = int(now_ts())
        end_req = intval(g("end"))
        mytime = end_req if 0 < end_req < now else now
        row = next((r for r in STATE["machine_time"] if r["id"] == key), None)
        just_closed = False
        if row and row["machine_end"] is None:
            row["machine_end"] = max(row["machine_start"], mytime)
            just_closed = True
        if not row:
            json_out(False, None, None, f"Session nicht gefunden (key={key} unitid={unitid})")
        finish_session(row, just_closed, mtype, unitid)

    if action == "offlineSession":
        now = int(now_ts())
        start, end = intval(g("start")), intval(g("end"))
        if start <= now - 30 * 86400 or start > now or end < start:
            json_out(False, None, None, "Parameter start/end ungueltig", 400)
        end = min(end, now)
        cands = find_members(rfid)
        cands.sort(key=lambda m: not card_active(m, rfid))
        if not cands:
            json_out(False, None, None, "Karte unbekannt", 404)
        member = cands[0]
        existing = [r for r in STATE["machine_time"] if r["cid"] == member["cid"] and r["machine_start"] == start]
        if existing:
            finish_session(existing[-1], False, mtype, unitid)
        STATE["next_id"]["machine_time"] += 1
        row = {"id": STATE["next_id"]["machine_time"], "cid": member["cid"], "unitid": unitid,
               "fname": member["firstName"], "lname": member["lastName"],
               "machine_start": start, "machine_end": end, "paid": None}
        STATE["machine_time"].append(row)
        finish_session(row, True, mtype, unitid)


# --------------------------------------------------------------------------- Fehlerinjektion
def pick_fault(action: str, unitid: int):
    """Erste passende, aktive Regel, die diesmal ausloest."""
    for f in STATE["faults"]:
        if not f["enabled"]:
            continue
        if f["action"] not in ("*", action):
            continue
        if f["unitid"] and f["unitid"] != unitid:
            continue
        if f["max_count"] and f["fired"] >= f["max_count"]:
            continue
        f["seen"] += 1
        if f["every_n"] > 1 and f["seen"] % f["every_n"] != 0:
            continue
        f["fired"] += 1
        return dict(f)
    return None


# --------------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "MockMARS/1.0"

    def log_message(self, *a):  # ruhig
        pass

    # -- Hilfen
    def _send(self, status, body: bytes, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode())

    def _drop(self):
        self.close_connection = True
        try:
            self.connection.shutdown(2)
        except OSError:
            pass
        self.connection.close()

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, (HERE / "gui.html").read_bytes(), "text/html; charset=utf-8")
        if url.path.startswith("/_gui/"):
            return self._gui_get(url)
        if url.path.endswith(".php"):
            return self._api(url)
        self._json({"ok": False, "msg": "not found"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        if not url.path.startswith("/_gui/"):
            return self._json({"ok": False, "msg": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json({"ok": False, "msg": "bad json"}, 400)
        with LOCK:
            try:
                res = gui_post(url.path[6:], data)
            except (KeyError, ValueError, TypeError) as err:
                return self._json({"ok": False, "msg": f"Fehler: {err!r}"}, 400)
        self._json(res)

    # -- API
    def _api(self, url):
        t0 = time.time()
        q = parse_qs(url.query, keep_blank_values=True)
        action = (q.get("action") or [""])[0]
        unitid = intval((q.get("unitid") or [0])[0])
        entry = {"t": fmt_ts(now_ts()), "ip": self.client_address[0], "action": action or "-",
                 "params": {k: v[0] for k, v in q.items() if k != "action"}, "fault": ""}

        with LOCK:
            latency = STATE["config"].get("latency_ms", 0)
            fault = pick_fault(action, unitid)
        if latency:
            time.sleep(latency / 1000)

        if fault:
            mode = fault["mode"]
            entry["fault"] = f"#{fault['id']} {mode}"
            if mode == "status":
                st = fault["status"]
                body = {"ok": False, "msg": "Simulierter Ausfall"}
                return self._finish(entry, t0, st, body)
            if mode == "badjson":
                return self._finish(entry, t0, 200, None, raw=b"<html><body>Oops, proxy error</body></html>",
                                    ctype="text/html")
            if mode == "empty":
                return self._finish(entry, t0, 200, None, raw=b"")
            if mode == "timeout":
                time.sleep(max(fault["delay_ms"], 1000) / 1000)
                entry.update(status="timeout", ms=int((time.time() - t0) * 1000), resp="")
                self._log(entry)
                return self._drop()
            if mode == "drop":
                entry.update(status="drop", ms=int((time.time() - t0) * 1000), resp="")
                self._log(entry)
                return self._drop()
            if mode == "lost_response":  # Aktion wird ausgefuehrt, Antwort geht verloren
                with LOCK:
                    status, body = handle_api(q, self.headers)
                entry.update(status="lost", ms=int((time.time() - t0) * 1000),
                             resp=f"(real {status}) " + json.dumps(body, ensure_ascii=False))
                self._log(entry)
                return self._drop()

        with LOCK:
            status, body = handle_api(q, self.headers)
            if status == 401:
                got, want = self.headers.get("X-MARS-Key", ""), STATE["config"]["api_key"]
                if not got:
                    entry["fault"] = "Key-Header fehlt/leer"
                elif got.strip() == want:
                    entry["fault"] = "Key hat Leerzeichen am Rand"
                else:
                    entry["fault"] = f"Key falsch ({len(got)} Zeichen, erwartet {len(want)})"
        self._finish(entry, t0, status, body)

    def _finish(self, entry, t0, status, body, raw=None, ctype=None):
        data = raw if raw is not None else json.dumps(body, ensure_ascii=False).encode()
        entry.update(status=status, ms=int((time.time() - t0) * 1000), resp=data.decode("utf-8", "replace")[:400])
        self._log(entry)
        self._send(status, data, ctype or "application/json; charset=utf-8")

    def _log(self, entry):
        with LOCK:
            REQUEST_LOG.appendleft(entry)

    # -- GUI
    def _gui_get(self, url):
        p = url.path[6:]
        with LOCK:
            if p == "state":
                s = copy.deepcopy(STATE)
                for m in s["members"]:
                    m["balance"] = current_payload(m["cid"])["payload"]
                s["mock_now"] = fmt_ts(now_ts())
                s["mock_weekday"] = DAYS[datetime.fromtimestamp(now_ts()).weekday()]
                s["ledger"] = s["ledger"][-200:][::-1]
                s["machine_time"] = s["machine_time"][-200:][::-1]
                s["access_log"] = s["access_log"][-200:][::-1]
                return self._json(s)
            if p == "log":
                return self._json(list(REQUEST_LOG))
            if p == "export":
                body = json.dumps(STATE, indent=1, ensure_ascii=False).encode()
                return self._send(200, body, extra={"Content-Disposition": 'attachment; filename="mock-scenario.json"'})
        self._json({"ok": False, "msg": "not found"}, 404)


def gui_post(path: str, d: dict) -> dict:
    global STATE
    if path == "config":
        c = STATE["config"]
        c["api_key"] = str(d.get("api_key", c["api_key"]))
        c["latency_ms"] = max(0, int(d.get("latency_ms", c["latency_ms"])))
        c["time_offset_s"] = int(d.get("time_offset_s", c["time_offset_s"]))
    elif path == "time_to":  # absolute Zeit setzen (Unix-Zeit)
        STATE["config"]["time_offset_s"] = int(float(d["ts"]) - time.time())
    elif path == "member":
        cid = int(d["cid"]) if d.get("cid") else max([m["cid"] for m in STATE["members"]] + [0]) + 1
        cards = [{"serial": s["serial"].strip(), "expired": bool(s.get("expired"))}
                 for s in d.get("cards", []) if s.get("serial", "").strip()]
        mships = [{"pid": int(x["pid"]), "name": str(x["name"])} for x in d.get("memberships", [])]
        new = {"cid": cid, "firstName": d["firstName"], "lastName": d["lastName"], "cards": cards,
               "memberships": mships, "trained": [int(u) for u in d.get("trained", [])],
               "blocked": bool(d.get("blocked")), "deleted": bool(d.get("deleted"))}
        old = member_by_cid(cid)
        if old:
            old.update(new)
        else:
            STATE["members"].append(new)
            write_payload(new, 0.0, 0, 0.0)
        if "balance" in d and d["balance"] != "":
            bal = float(d["balance"])
            cur = float(current_payload(cid)["payload"])
            if bal != cur:
                write_payload(new, bal, 0, php_round1(bal - cur))
    elif path == "units":
        STATE["units"] = [{"unitid": int(u["unitid"]), "name": str(u["name"]),
                           "type": u["type"] if u["type"] in TYPES + ("door", "coffee") else "machine"}
                          for u in d["units"]]
    elif path == "member_delete":
        STATE["members"] = [m for m in STATE["members"] if m["cid"] != int(d["cid"])]
    elif path == "prices":
        STATE["prices"] = {str(k): {c: float(v[c]) for c in ("laser_full", "3dprint_min", "dtf_drucker_min")}
                           for k, v in d["prices"].items()}
    elif path == "fault":
        f = {"action": d.get("action", "*"), "unitid": int(d.get("unitid") or 0),
             "mode": d.get("mode", "status"), "status": int(d.get("status") or 503),
             "delay_ms": int(d.get("delay_ms") or 30000), "every_n": max(1, int(d.get("every_n") or 1)),
             "max_count": max(0, int(d.get("max_count") or 0)), "enabled": bool(d.get("enabled", True))}
        if f["mode"] not in ("status", "timeout", "drop", "badjson", "empty", "lost_response"):
            raise ValueError("mode")
        if d.get("id"):
            old = next(x for x in STATE["faults"] if x["id"] == int(d["id"]))
            old.update(f)
        else:
            STATE["faults"].append({**f, "id": STATE["next_id"]["fault"], "seen": 0, "fired": 0})
            STATE["next_id"]["fault"] += 1
    elif path == "fault_delete":
        STATE["faults"] = [f for f in STATE["faults"] if f["id"] != int(d["id"])]
    elif path == "fault_clear":
        STATE["faults"] = []
    elif path == "clear":
        what = d["what"]
        if what == "log":
            REQUEST_LOG.clear()
        elif what in ("machine_time", "access_log"):
            STATE[what] = []
    elif path == "close_session":  # offene Session ohne Abrechnung abbrechen (Test von 'verwaist')
        STATE["machine_time"] = [r for r in STATE["machine_time"] if r["id"] != int(d["id"])]
    elif path == "reset":
        STATE = seed_state()
        REQUEST_LOG.clear()
    elif path == "import":
        new = d["state"]
        for k in ("config", "prices", "members", "faults", "machine_time", "ledger", "access_log", "next_id"):
            if k not in new:
                raise KeyError(k)
        new.setdefault("units", seed_state()["units"])
        STATE = new
    else:
        raise KeyError(path)
    return {"ok": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="0.0.0.0", help="Bind-Adresse (Standard: alle Interfaces)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--key", default=None, help="API-Key (Standard: test-key)")
    ap.add_argument("--state", default=None, help="Szenario-JSON (Export aus der GUI) laden")
    a = ap.parse_args()
    if a.state:
        gui_post("import", {"state": json.loads(Path(a.state).read_text(encoding="utf-8"))})
    if a.key is not None:
        STATE["config"]["api_key"] = a.key
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    srv.daemon_threads = True
    print(f"MARS-Mock laeuft: GUI http://localhost:{a.port}/  API http://<ip>:{a.port}/machineswitch.php  "
          f"Key '{STATE['config']['api_key']}'")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
