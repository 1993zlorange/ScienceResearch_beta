"""Start the target FastAPI runtime while retaining the Flask compatibility option."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "apps" / "api" / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the ScienceResearch target API server")
    parser.add_argument("--runtime", choices=("fastapi", "flask"), default="fastapi")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "storage" / "runtime")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reload", action="store_true", help="enable Uvicorn autoreload for local development")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.runtime == "fastapi":
        import uvicorn
        from scienceresearch.main import create_app

        uvicorn.run(
            create_app(legacy_data_dir=args.data_dir),
            host=args.host,
            port=args.port,
            reload=args.reload,
            factory=False,
        )
        return 0

    from scienceresearch.flask_app import create_app
    from waitress import serve

    serve(create_app(data_dir=args.data_dir), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
