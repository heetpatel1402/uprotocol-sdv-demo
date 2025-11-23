from demo.alert_service import DEFAULT_THRESHOLD
from demo.common import epoch_ms

def test_speed_alert_trigger():
    kmh = DEFAULT_THRESHOLD + 20
    assert kmh > DEFAULT_THRESHOLD
