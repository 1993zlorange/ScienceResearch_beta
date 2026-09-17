from __future__ import annotations
import json
from pathlib import Path
from .adapters.legacy_service import ResearchWorkbench
def create_workbench(data_dir: Path) -> ResearchWorkbench:
    """Compose the application service for local deployment."""
    bootstrap = data_dir / "operations.json"
    business_root = data_dir
    if bootstrap.exists():
        try:
            configured = json.loads(bootstrap.read_text(encoding="utf-8")).get("business_root", "")
            if configured:
                candidate = Path(configured).expanduser().resolve()
                if "release" not in {part.lower() for part in candidate.parts}:
                    business_root = candidate
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return ResearchWorkbench(business_root / "scienceresearch.db", business_root / "artifacts", bootstrap_dir=data_dir)
