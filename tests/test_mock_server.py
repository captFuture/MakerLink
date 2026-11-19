"""Tests fuer tools/mock_server/server.py (Nachbau von machineswitch.php)."""

from __future__ import annotations

import importlib.util
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "tools" / "mock_server" / "server.py"
spec = importlib.util.spec_from_file_location("mock_server", SRC)
srv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)

MAX = "0xf4 0x96 0xd2 0x28"  # Unlimited, Guthaben 50
ERIKA = "0x1 0x2 0x3 0x4"  # Basic, 20
LEO = "0x9 0xa 0xb 0xc"  # Guthaben 0
BERND = "0xd 0xe 0xf 0x10"  # blockiert
HANNA = "0x11 0x12 0x13 0x14"  # keine Schulung
LISA = "0x15 0x16 0x17 0x18"  # Mon/Wed 18-22


@pytest.fixture(autouse=True)
def fresh():
    srv.STATE = srv.seed_state()
    srv.REQUEST_LOG.clear()


def call(**params):
    q = {k: [str(v)] for k, v in params.items()}
    status, body = srv.handle_api(q, {"X-MARS-Key": srv.STATE["config"]["api_key"]})
    return status, body


def balance(cid):
    return srv.current_payload(cid)["payload"]


def test_auth():
    assert srv.handle_api({}, {})[0] == 401
    assert srv.handle_api({}, {"X-MARS-Key": "falsch"})[0] == 401
    assert call()[0] == 400  # Verbindungstest der Integration
    srv.STATE["config"]["api_key"] = "CHANGEME"
    assert srv.handle_api({}, {"X-MARS-Key": "CHANGEME"})[0] == 500


def test_param_validation():
    assert call(action="start", rfid=MAX)[0] == 400  # unitid fehlt
    assert call(action="start", unitid=1720, type="foo", rfid=MAX)[0] == 400
    assert call(action="start", unitid=1720)[0] == 400
    assert call(action="stop", unitid=1720)[0] == 400
    assert call(action="logDoorAccess", rfid=MAX, status="TRUE", unitid=1, check=1)[0] == 400


def test_laser_start_stop_billing():
    s, b = call(action="start", rfid=MAX, unitid=1720, type="laser")
    assert (s, b["ok"], b["msg"], b["name"]) == (200, True, "Aktiviert", "Max")
    key = b["key"]
    srv.STATE["config"]["time_offset_s"] += 16 * 60  # 16 min -> 2 Viertelstunden
    s, b = call(action="stop", key=key, unitid=1720, type="laser")
    assert b["ok"] and b["use_units"] == 2
    assert b["cost"] == 0.0 and balance(1) == 50.0  # Unlimited zahlt 0
    # Idempotent
    assert call(action="stop", key=key, unitid=1720, type="laser")[1]["already_stopped"] is True
    assert balance(1) == 50.0


def test_laser_basic_pays_per_quarter_hour():
    s, b = call(action="start", rfid=ERIKA, unitid=1720, type="laser")
    srv.STATE["config"]["time_offset_s"] += 16 * 60
    b = call(action="stop", key=b["key"], unitid=1720, type="laser")[1]
    assert b["cost"] == -5.0 and b["balance"] == 15.0  # 2 x 2.50


def test_3dprint_per_minute_and_stop_with_end():
    b = call(action="start", rfid=ERIKA, unitid=1721, type="3dprint")[1]
    start = srv.STATE["machine_time"][-1]["machine_start"]
    srv.STATE["config"]["time_offset_s"] += 600  # end liegt sonst in der Zukunft -> ignoriert
    b = call(action="stop", key=b["key"], unitid=1721, type="3dprint", end=start + 61)[1]
    assert b["use_units"] == 2 and b["cost"] == -0.2  # 2 min x 0.10


def test_kiln_fixed_price():
    b = call(action="start", rfid=ERIKA, unitid=1722, type="kiln")
    assert b[1]["ok"] is False  # Erika ist nicht geschult
    b = call(action="start", rfid=MAX, unitid=1722, type="kiln")[1]
    srv.STATE["members"][0]["memberships"] = [{"pid": 2, "name": "Basic"}]  # Basic zahlt
    b = call(action="stop", key=b["key"], unitid=1722, type="kiln")[1]
    assert b["cost"] == -40.0 and b["balance"] == 10.0


def test_machine_is_free_and_idempotent():
    b = call(action="start", rfid=ERIKA, unitid=1730, type="machine")[1]
    assert b["ok"]
    s = call(action="stop", key=b["key"], unitid=1730, type="machine")[1]
    assert s["msg"] == "Gestoppt" and s["cost"] == 0.0 and balance(2) == 20.0
    assert call(action="stop", key=b["key"], unitid=1730, type="machine")[1]["already_stopped"]


def test_coffee_debits_immediately():
    b = call(action="start", rfid=ERIKA, unitid=6, type="machine", min_balance=0.5)[1]
    assert b["ok"] and b["key"] is None and b["cost"] == -0.5 and b["balance"] == 19.5


def test_start_rejections():
    assert call(action="start", rfid="0x0", unitid=1720, type="laser")[1]["msg"].startswith("Karte unbekannt")
    assert "blockiert" in call(action="start", rfid=BERND, unitid=1720, type="laser")[1]["msg"]
    assert "reicht nicht" in call(action="start", rfid=LEO, unitid=1720, type="laser")[1]["msg"]
    assert call(action="start", rfid=HANNA, unitid=1720, type="laser")[1]["msg"] == "Keine Schulung fuer diese Maschine"
    # Maschine mit Guthaben 0 und min_balance 0: erlaubt
    assert call(action="start", rfid=LEO, unitid=1730, type="machine", min_balance=0)[1]["ok"]


def test_stop_unknown_session_is_200_not_ok():
    s, b = call(action="stop", key=424242, unitid=1720, type="laser")
    assert s == 200 and b["ok"] is False and "nicht gefunden" in b["msg"]


def test_offline_session_idempotent():
    now = int(srv.now_ts())
    p = dict(action="offlineSession", rfid=ERIKA, unitid=1720, type="laser", start=now - 3600, end=now - 3000)
    b1 = call(**p)[1]
    assert b1["ok"] and b1["use_units"] == 1 and b1["cost"] == -2.5  # 10 min = 1 Viertelstunde
    bal = balance(2)
    assert call(**p)[1]["already_stopped"] is True and balance(2) == bal
    assert call(**{**p, "rfid": "0x0"})[0] == 404
    assert call(**{**p, "start": now - 40 * 86400})[0] == 400
    assert call(**{**p, "end": now - 4000})[0] == 400


def test_door():
    assert call(action="doorLockCheck", rfid=MAX)[1][:2] == ["True", "Super User"]
    assert call(action="doorLockCheck", rfid=BERND)[1][0] == "False"
    assert call(action="doorLockCheck", rfid="0x0")[1][0] == "False"
    srv.STATE["members"][1]["cards"][0]["expired"] = True
    assert call(action="doorLockCheck", rfid=ERIKA)[1][0] == "False"
    # Limited Lisa: Montag 20 Uhr ja, Montag 23 Uhr nein, Dienstag nein
    import datetime as dt
    mon = dt.datetime(2026, 11, 16, 20, 0).timestamp()  # 2026-11-16 ist ein Montag
    srv.STATE["config"]["time_offset_s"] = int(mon - time.time())
    assert call(action="doorLockCheck", rfid=LISA)[1][:2] == ["True", "Limited User"]
    srv.STATE["config"]["time_offset_s"] += 3 * 3600
    assert call(action="doorLockCheck", rfid=LISA)[1][1] == "Wrong Time"
    srv.STATE["config"]["time_offset_s"] += 86400
    assert call(action="doorLockCheck", rfid=LISA)[1][1] == "Wrong Day"


def test_log_door_access_and_whitelist():
    assert call(action="logDoorAccess", rfid=MAX, status="true", unitid=1, check=2)[1]["ok"]
    assert srv.STATE["access_log"][-1]["status"] == 1 and srv.STATE["access_log"][-1]["cid"] == 1
    wl = call(action="whitelist")[1]
    assert wl["cards"] == [MAX] and wl["count"] == 1  # Bernd ist blockiert


def test_fault_rules():
    f = {"id": 1, "enabled": True, "action": "stop", "unitid": 0, "mode": "status", "status": 503,
         "delay_ms": 0, "every_n": 2, "max_count": 1, "seen": 0, "fired": 0}
    srv.STATE["faults"] = [f]
    assert srv.pick_fault("start", 1720) is None  # falsche Aktion
    assert srv.pick_fault("stop", 1720) is None  # 1. Treffer: n=2 -> noch nicht
    assert srv.pick_fault("stop", 1720)["id"] == 1  # 2.
    assert srv.pick_fault("stop", 1720) is None  # max_count erreicht
    assert srv.pick_fault("stop", 1720) is None


def test_http_end_to_end():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/machineswitch.php?action=whitelist", headers={"X-MARS-Key": "test-key"})
        assert json.load(urllib.request.urlopen(req))["count"] == 1
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/machineswitch.php?action=whitelist")
        assert e.value.code == 401
        # Fehlerinjektion ueber die GUI-API, danach 503
        post = urllib.request.Request(base + "/_gui/fault", data=json.dumps({"action": "*", "mode": "status"}).encode())
        urllib.request.urlopen(post)
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 503
        assert b"MARS Mock" in urllib.request.urlopen(base + "/").read()
        assert len(json.load(urllib.request.urlopen(base + "/_gui/log"))) == 3
    finally:
        httpd.shutdown()
