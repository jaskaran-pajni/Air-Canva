import os
from dataclasses import dataclass

@dataclass
class Config:
    # --- Camera ---
    # Set to 1 for MacBook FaceTime camera, 0 for external Logitech
    camera_index: int = 0
    width: int = 1920
    height: int = 1080
    fps_limit: int = 15

    # --- Default Mode ---
    # "motion" or "gesture"
    default_mode: str = "motion"

    # --- Storage ---
    # Ensure these paths match your folder structure exactly
    log_path: str = os.path.join("logs", "events.jsonl")
    snapshot_dir: str = "snapshots"
    max_events_in_memory: int = 200

    # --- Server ---
    # 0.0.0.0 allows access from other devices on your Wi-Fi
    host: str = "0.0.0.0" 
    port: int = 5050

CFG = Config()
