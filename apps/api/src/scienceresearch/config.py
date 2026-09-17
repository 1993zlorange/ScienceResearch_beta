from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8765
