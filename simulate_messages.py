# demo/simulate_messages.py
import uuid
import time
import json

def uuri_str(authority, ue_id, resource, vmajor=1):
    # Simple string format for demo purposes
    return f"up://{authority}/{ue_id}{resource}?v={vmajor}"

def uevent(topic_uri, payload_dict):
    return {
        "type": "EVENT",
        "id": str(uuid.uuid4()),
        "source": uuri_str("car-01", "vehicle.telemetry", "/publisher"),
        "target": topic_uri,
        "content_type": "application/json",
        "payload": payload_dict,  # would be bytes in real system
        "qos": 0,
        "ttl_ms": 2000,
    }

def urequest(method_uri, payload_dict):
    msg_id = str(uuid.uuid4())
    return {
        "type": "REQUEST",
        "id": msg_id,
        "source": uuri_str("car-01", "mobile.app", "/client"),
        "target": method_uri,
        "content_type": "application/json",
        "payload": payload_dict,
        "qos": 1,
        "ttl_ms": 3000,
    }

def uresponse(request_id, to_uri, status_dict, result_dict=None):
    return {
        "type": "RESPONSE",
        "id": str(uuid.uuid4()),
        "correlation_id": request_id,  # pairs the response to the request
        "source": uuri_str("car-01", "body.control", "/service"),
        "target": to_uri,
        "content_type": "application/json",
        "status": status_dict,  # standardized status
        "payload": result_dict or {},
    }

def main():
    # ---- Event example: speed telemetry ----
    topic = uuri_str("car-01", "vehicle.telemetry", "/speed")
    speed_evt = uevent(topic, {"kmh": 72, "timestamp_ms": int(time.time() * 1000)})
    print("EVENT ->", json.dumps(speed_evt, indent=2))

    # ---- RPC example: lock doors ----
    lock_uri = uuri_str("car-01", "body.control", "/doors/lock")
    req = urequest(lock_uri, {"lock": True})
    print("REQUEST ->", json.dumps(req, indent=2))

    # Fake the service handling and replying OK
    resp = uresponse(
        request_id=req["id"],
        to_uri=req["source"],
        status_dict={"code": "OK", "message": "Doors locked"},
        result_dict={"success": True}
    )
    print("RESPONSE ->", json.dumps(resp, indent=2))

if __name__ == "__main__":
    main()
