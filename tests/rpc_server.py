# ... continuing test_core_logic.py

def test_handle_lock_success():
    """FR-2: Doors lock handler returns OK and success=True."""
    req = {"method": "lock"}
    res = handle_lock(req)
    
    assert res["success"] is True
    assert res["status"]["code"] == "OK"
    assert "Doors locked" in res["status"]["message"]


def test_handle_set_speed_limit_success(mock_config_store):
    """FR-7: Speed limit is set and effective limit is returned."""
    mock_set, _, mock_get_effective = mock_config_store
    mock_get_effective.return_value = 120.0 # Simulate the new effective limit

    req = {"method": "set_speed_limit", "payload": {"limit_kmh": 120}}
    res = handle_set_speed_limit(req)
    
    # Assert the mock function was called with the correct value
    mock_set.assert_called_with(120)
    
    assert res["success"] is True
    assert res["status"]["code"] == "OK"
    assert res["effective_limit"] == 120.0


@pytest.mark.parametrize("limit_val", [None, "invalid", "10.5"])
def test_handle_set_speed_limit_validation_failure(limit_val):
    """FR-7: Handle missing or non-integer speed limit."""
    req = {"method": "set_speed_limit", "payload": {"limit_kmh": limit_val}}
    res = handle_set_speed_limit(req)
    
    assert "ERR" in res["status"]["code"]
    assert "missing" in res["status"]["message"] or "invalid" in res["status"]["message"]


def test_handle_get_config_success(mock_config_store):
    """FR-9: Returns config snapshot and effective limit."""
    _, mock_get_snapshot, mock_get_effective = mock_config_store
    mock_get_snapshot.return_value = {"rpc_speed_limit": 100, "current_zone": "School"}
    mock_get_effective.return_value = 40.0 # Effective limit from mock

    req = {"method": "get_config"}
    res = handle_get_config(req)
    
    assert res["status"]["code"] == "OK"
    assert res["config"]["current_zone"] == "School"
    assert res["config"]["effective_limit"] == 40.0
