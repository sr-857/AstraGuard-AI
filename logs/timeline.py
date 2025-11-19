
#!/usr/bin/env python3
import time, os
LOG_PATH = os.path.join(os.path.dirname(__file__),"event_log.txt")

def log_event(event_type, details):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    entry = f"{ts} | {event_type} | {details}\n"
    with open(LOG_PATH, "a") as f:
        f.write(entry)

def read_recent(n=20):
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        lines = f.read().strip().splitlines()
    return lines[-n:]
