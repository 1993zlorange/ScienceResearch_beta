from __future__ import annotations

import sys
from pathlib import Path


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[4] / "storage" / "runtime"


def main() -> int:
    """Route web options to the server and all other options to the CLI."""
    if "--host" in sys.argv or "--port" in sys.argv:
        import argparse
        from .flask_app import create_app

        parser = argparse.ArgumentParser(description="科研工作台离线 Web")
        parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8765)
        args = parser.parse_args()
        from waitress import serve
        serve(create_app(data_dir=args.data_dir), host=args.host, port=args.port)
        return 0

    from .cli import main as cli_main
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
