import json
from demo.config_store import set_rpc_speed_limit, get_effective_speed_limit

def test_rpc_speed_limit_updates_config():
    set_rpc_speed_limit(55)
    eff = get_effective_speed_limit(default_threshold=80)
    assert eff == 55, "RPC limit should override default threshold"
