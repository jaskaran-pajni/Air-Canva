import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

Event = Dict[str, Any]

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class EventStore:
    def __init__(self, log_path: str, maxlen: int = 200):
        self.log_path = log_path
        self._lock = threading.Lock()
        self._events: Deque[Event] = deque(maxlen=maxlen)

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # Ensure file exists
        if not os.path.exists(log_path):
            with open(log_path, "w", encoding="utf-8") as f:
                pass


    def add(self, event: Event) -> None:
        # Ensure required fields exist
        event = dict(event)
        event.setdefault("timestamp", utc_iso())
        event.setdefault("confidence", None)

        line = json.dumps(event, ensure_ascii=False)

        with self._lock:
            self._events.append(event)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def latest(self, n: int = 50) -> List[Event]:
        with self._lock:
            return list(self._events)[-n:]

    def clear_memory(self) -> None:
        with self._lock:
            self._events.clear()
            
            
