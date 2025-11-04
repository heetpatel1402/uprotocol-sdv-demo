# FR-1: Verify speed event schema produced by the publisher helpers
from demo.pub_telemetry import build_speed_event, uuri

def test_build_speed_event_schema():
    evt = build_speed_event(72)
    assert evt["type"] == "EVENT"
    assert isinstance(evt["id"], str) and len(evt["id"]) >= 8
    assert evt["payload"]["kmh"] == 72
    assert isinstance(evt["payload"]["timestamp_ms"], int)

    # URIs look like up://car-01/vehicle.telemetry/speed?v=1
    assert evt["source"].startswith("up://") and "?v=" in evt["source"]
    assert evt["target"].startswith("up://") and "/speed" in evt["target"]

def test_uuri_format():
    s = uuri("car-01", "vehicle.telemetry", "/speed", v=1)
    assert s.startswith("up://car-01/vehicle.telemetry/speed")
    assert s.endswith("?v=1")
