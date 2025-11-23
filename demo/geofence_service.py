# demo/geofence_service.py
from __future__ import annotations

import time
from typing import List, Tuple

try:
    from demo.config_store import set_geo_context
except ImportError:
    from config_store import set_geo_context

# (zone_name, speed_limit_kmh, duration_seconds)
ZONES: List[Tuple[str, int, int]] = [
    ("City", 50, 15),
    ("Highway", 100, 20),
    ("School", 30, 15),
]


def main():
    print("[geo] starting geofence simulator (cycling zones)…", flush=True)
    while True:
        for name, limit, duration in ZONES:
            print(f"[geo] entering zone '{name}' with limit {limit} km/h for {duration}s", flush=True)
            set_geo_context(name, limit)
            time.sleep(duration)


if __name__ == "__main__":
    main()

# import time
# from typing import List, Tuple

# try:
#     # when running from project root
#     from demo.config_store import set_geo_context
# except ImportError:  # running from inside demo/
#     from config_store import set_geo_context

# # (zone_name, speed_limit_kmh, duration_seconds)
# ZONES: List[Tuple[str, int, int]] = [
#     ("City", 50, 15),
#     ("Highway", 100, 20),
#     ("School", 30, 15),
# ]


# def main():
#     print("[geo] starting geofence simulator (cycling zones)…", flush=True)
#     while True:
#         for name, limit, duration in ZONES:
#             print(f"[geo] entering zone '{name}' with limit {limit} km/h for {duration}s", flush=True)
#             set_geo_context(name, limit)
#             time.sleep(duration)


# if __name__ == "__main__":
#     main()
