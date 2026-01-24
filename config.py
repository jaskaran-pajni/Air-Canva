from dataclasses import dataclass

@dataclass
class Config:
    # Camera
    camera_index: int = 0
    width: int = 640
    height: int = 360
    fps_limit: int = 15

    # Default mode: "motion" or "gesture"
    default_mode: str = "motion"

    # Storage
    log_path: str = "logs/events.jsonl"
    snapshot_dir: str = "snapshots"
    max_events_in_memory: int = 200

    # Server
    host: str = "0.0.0.0"
    port: int = 5000

CFG = Config()
