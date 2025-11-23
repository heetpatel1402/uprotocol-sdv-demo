from demo.rpc_server import handle_lock

def test_rpc_lock_response():
    res = handle_lock({"method": "lock"})
    assert res["success"] is True
    assert res["status"]["code"] == "OK"
