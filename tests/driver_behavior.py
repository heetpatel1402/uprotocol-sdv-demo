# ... continuing test_core_logic.py

@pytest.fixture
def mock_alert_log(tmp_path):
    """Fixture to create a temporary, mocked ALERT_LOG file."""
    # Patch the internal path used by the driver_behavior module
    with patch('demo.driver_behavior.ALERT_LOG', tmp_path / "alerts.jsonl"), \
         patch('demo.driver_behavior.epoch_ms', return_value=1678886400000): # Fixed time
        
        # Ensure the logs directory exists for audit_write
        Path("logs").mkdir(exist_ok=True)
        
        # Mock the file object for writing alerts
        mock_log = tmp_path / "alerts.jsonl"
        
        # Set the mock return value for the function used to load alerts (if needed)
        yield mock_log

def _write_mock_alert(log_file: Path, zone: str, score_ts_offset_ms: int):
    """Helper to write a mock alert with a specific zone and timestamp."""
    base_ts = 1678886400000
    alert = {
        "timestamp_ms": base_ts - score_ts_offset_ms,
        "zone": zone,
        "kmh": 100,
        "limit": 80
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


def test_driver_behavior_safe(mock_alert_log):
    """Score 0-3 -> Safe level."""
    # Write one highway alert (score +1) inside the 10-second window
    _write_mock_alert(mock_alert_log, zone="highway", score_ts_offset_ms=5000) 
    
    result = compute_driver_behavior()
    assert result["score"] == 1
    assert result["level"] == "safe"
    assert result["label"] == "🟢 Safe"
    assert result["alert_count"] == 1


def test_driver_behavior_risky(mock_alert_log):
    """Score 8+ -> Risky level."""
    # Write three school zone alerts (3 * +3 = 9) inside the window
    _write_mock_alert(mock_alert_log, zone="school", score_ts_offset_ms=1000)
    _write_mock_alert(mock_alert_log, zone="school", score_ts_offset_ms=2000)
    _write_mock_alert(mock_alert_log, zone="school", score_ts_offset_ms=3000)
    
    result = compute_driver_behavior()
    assert result["score"] == 9
    assert result["level"] == "risky"
    assert result["label"] == "🔴 Risky"
    assert result["alert_count"] == 3


def test_driver_behavior_window(mock_alert_log):
    """Alerts outside the 10-second window are ignored."""
    # Write one alert just outside the window (11 seconds ago)
    _write_mock_alert(mock_alert_log, zone="city", score_ts_offset_ms=11000) 
    # Write one alert just inside the window (9 seconds ago)
    _write_mock_alert(mock_alert_log, zone="city", score_ts_offset_ms=9000)
    
    result = compute_driver_behavior()
    assert result["score"] == 2 # Only the recent city alert (score +2) should count
    assert result["alert_count"] == 1
