import os
from dataclasses import dataclass

@dataclass
class Config:
    # --- Camera ---
    camera_index: int = 0
    width: int = 1920
    height: int = 1080
    fps_limit: int = 15

    # --- Default Mode ---
    default_mode: str = "motion"

    # --- Storage ---
    log_path: str = os.path.join("logs", "events.jsonl")
    snapshot_dir: str = "snapshots"
    max_events_in_memory: int = 200

    # --- Server ---
    # Use environment variable PORT for Render, fallback to 5050 for local
    host: str = "0.0.0.0"
    port: int = int(os.environ.get("PORT", 5050))

CFG = Config()