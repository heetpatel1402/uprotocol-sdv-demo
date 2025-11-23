from demo.config_store import (
    set_geo_context,
    set_rpc_speed_limit,
    get_effective_speed_limit,
)

def test_effective_limit_priority_geofence():
    # RPC lower, geofence higher precedence
    set_rpc_speed_limit(70)
    set_geo_context("City", 50)
    eff = get_effective_speed_limit(default_threshold=80)
    assert eff == 50, "Geofence must override RPC"

def test_effective_limit_priority_rpc():
    # No geofence → RPC applies
    set_geo_context(None, None)
    set_rpc_speed_limit(60)
    eff = get_effective_speed_limit(default_threshold=80)
    assert eff == 60

def test_effective_limit_priority_default():
    # Neither geofence nor RPC → default
    set_geo_context(None, None)
    set_rpc_speed_limit(None)
    eff = get_effective_speed_limit(default_threshold=90)
    assert eff == 90
