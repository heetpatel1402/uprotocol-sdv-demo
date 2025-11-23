from demo.config_store import set_geo_context, get_config_snapshot

def test_geofence_zone_updates_config():
    set_geo_context("School", 30)
    cfg = get_config_snapshot()
    assert cfg["current_zone"] == "School"
    assert cfg["geo_speed_limit"] == 30
