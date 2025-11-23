# demo/pub_telemetry.py
import socket
import json
import time
import uuid
import random

# Alert service listens on 50052
# Status summary listens on 50056
DESTS = [
    ("127.0.0.1", 50052),  # alert_service
    ("127.0.0.1", 50056),  # status_summary
]


def uuri(authority, ue_id, resource, v=1):
    return f"up://{authority}/{ue_id}{resource}?v={v}"


def build_speed_event(kmh: int):
    lat = 43.7 + random.uniform(-0.05, 0.05)
    lon = -79.4 + random.uniform(-0.05, 0.05)

    return {
        "type": "EVENT",
        "id": str(uuid.uuid4()),
        "source": uuri("car-01", "vehicle.telemetry", "/publisher"),
        "target": uuri("car-01", "vehicle.telemetry", "/speed"),
        "content_type": "application/json",
        "payload": {
            "kmh": kmh,
            "timestamp_ms": int(time.time() * 1000),
            "lat": lat,
            "lon": lon,
        },
        "qos": 0,
        "ttl_ms": 2000,
    }


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest_str = ", ".join([f"udp://{h}:{p}" for h, p in DESTS])
    print(f"[pub] sending to {dest_str} every 1s. Ctrl+C to stop.")
    while True:
        kmh = random.randint(20, 120)
        msg = build_speed_event(kmh)
        raw = json.dumps(msg).encode("utf-8")
        for host, port in DESTS:
            sock.sendto(raw, (host, port))
        print(f"[pub] -> speed {kmh} km/h (id={msg['id'][:8]}...)", flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
# # demo/pub_telemetry.py
# import socket, json, time, uuid, random

# SUB_PORT = 50052  # where subscriber/geofence/summary/alert listen


# def uuri(authority, ue_id, resource, v=1):
#     return f"up://{authority}/{ue_id}{resource}?v={v}"


# def build_speed_event(kmh: int):
#     # Mock some simple lat/lon around Toronto-ish for geofencing
#     lat = 43.7 + random.uniform(-0.05, 0.05)
#     lon = -79.4 + random.uniform(-0.05, 0.05)

#     return {
#         "type": "EVENT",
#         "id": str(uuid.uuid4()),
#         "source": uuri("car-01", "vehicle.telemetry", "/publisher"),
#         "target": uuri("car-01", "vehicle.telemetry", "/speed"),
#         "content_type": "application/json",
#         "payload": {
#             "kmh": kmh,
#             "timestamp_ms": int(time.time() * 1000),
#             "lat": lat,
#             "lon": lon,
#         },
#         "qos": 0,
#         "ttl_ms": 2000,
#     }


# def main():
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     print(f"[pub] sending to udp://127.0.0.1:{SUB_PORT} every 1s. Ctrl+C to stop.")
#     while True:
#         kmh = random.randint(20, 120)
#         msg = build_speed_event(kmh)
#         sock.sendto(json.dumps(msg).encode("utf-8"), ("127.0.0.1", SUB_PORT))
#         print(f"[pub] -> speed {kmh} km/h (id={msg['id'][:8]}...)", flush=True)
#         time.sleep(1)


# if __name__ == "__main__":
#     main()

# # # demo/pub_telemetry.py
# # import socket, json, time, uuid, random

# # SUB_PORT = 50052  # where subscriber is listening

# # def uuri(authority, ue_id, resource, v=1):
# #     return f"up://{authority}/{ue_id}{resource}?v={v}"

# # def build_speed_event(kmh: int):
# #     return {
# #         "type": "EVENT",
# #         "id": str(uuid.uuid4()),
# #         "source": uuri("car-01", "vehicle.telemetry", "/publisher"),
# #         "target": uuri("car-01", "vehicle.telemetry", "/speed"),
# #         "content_type": "application/json",
# #         "payload": {"kmh": kmh, "timestamp_ms": int(time.time() * 1000)},
# #         "qos": 0,
# #         "ttl_ms": 2000,
# #     }

# # def main():
# #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #     print(f"[pub] sending to udp://127.0.0.1:{SUB_PORT} every 1s. Ctrl+C to stop.")
# #     while True:
# #         kmh = random.randint(20, 120)
# #         msg = build_speed_event(kmh)
# #         sock.sendto(json.dumps(msg).encode("utf-8"), ("127.0.0.1", SUB_PORT))
# #         print(f"[pub] -> speed {kmh} km/h (id={msg['id'][:8]}...)")
# #         time.sleep(1)

# # if __name__ == "__main__":
# #     main()
