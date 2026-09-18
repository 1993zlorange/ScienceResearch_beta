"""Build reproducible offline runtime assets for the technical documentation page."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path("config/technical-manuals.json")


@dataclass(frozen=True, slots=True)
class ManualConfig:
    manual_id: str
    title: str
    description: str
    source: Path
    version: str
    output_filename: str
    sha256: str


class TechnicalManualBuildError(RuntimeError):
    """Raised when a source, output path, or generated asset violates the build contract."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the offline technical manual runtime assets")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="ScienceResearch project root")
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="manifest source config relative to project root"
    )
    parser.add_argument("--check", action="store_true", help="validate sources and existing outputs without writing")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="reuse hash-validated outputs when formal sources are not packaged",
    )
    return parser


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TechnicalManualBuildError(f"{field} must be a non-empty string")
    return value


def _load_config(config_path: Path, project_root: Path) -> tuple[str, Path, list[ManualConfig]]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TechnicalManualBuildError(f"cannot read config {config_path}: {error}") from error
    if not isinstance(raw, dict):
        raise TechnicalManualBuildError("technical manual config must be an object")
    version = _text(raw.get("version"), "version")
    output_root_value = _text(raw.get("output_root"), "output_root")
    output_root = _resolve_managed(output_root_value, project_root, project_root)
    raw_manuals = raw.get("manuals")
    if not isinstance(raw_manuals, list) or not raw_manuals:
        raise TechnicalManualBuildError("manuals must be a non-empty array")
    manuals = [_manual(item, project_root) for item in raw_manuals]
    ids = [manual.manual_id for manual in manuals]
    filenames = [manual.output_filename for manual in manuals]
    if len(set(ids)) != len(ids) or len(set(filenames)) != len(filenames):
        raise TechnicalManualBuildError("manual ids and output filenames must be unique")
    return version, output_root, manuals


def _manual(value: Any, project_root: Path) -> ManualConfig:
    if not isinstance(value, dict):
        raise TechnicalManualBuildError("each manual must be an object")
    source_value = _text(value.get("source"), "manual.source")
    source = _resolve_source(source_value, project_root)
    output_filename = _text(value.get("output_filename"), "manual.output_filename")
    if Path(output_filename).name != output_filename or output_filename in {".", ".."}:
        raise TechnicalManualBuildError("manual.output_filename must be a safe basename")
    return ManualConfig(
        manual_id=_text(value.get("id"), "manual.id"),
        title=_text(value.get("title"), "manual.title"),
        description=_text(value.get("description"), "manual.description"),
        source=source,
        version=_text(value.get("version"), "manual.version"),
        output_filename=output_filename,
        sha256=_text(value.get("sha256"), "manual.sha256").upper(),
    )


def _resolve_source(value: str, project_root: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts[1:]:
        raise TechnicalManualBuildError("manual.source must be a repository-relative path")
    allowed_source = candidate.parts[:3] == ("..", "achieve", "04-交付与阶段") or candidate.parts[0] == "docs"
    if not allowed_source:
        raise TechnicalManualBuildError("manual.source must be under project docs or formal achieve delivery")
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.parent)
    except ValueError as error:
        raise TechnicalManualBuildError("manual.source escapes the repository root") from error
    return resolved


def _resolve_managed(value: str, project_root: Path, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise TechnicalManualBuildError("managed path must be project-relative")
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as error:
        raise TechnicalManualBuildError("managed path escapes the project root") from error
    return resolved


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _read_validated_source(manual: ManualConfig, output_root: Path, *, reuse_existing: bool = False) -> bytes:
    try:
        data = manual.source.read_bytes()
    except OSError as error:
        if not reuse_existing:
            raise TechnicalManualBuildError(f"cannot read source {manual.source.name}: {error}") from error
        return _read_existing_output(manual, output_root)
    digest = _sha256(data)
    if digest != manual.sha256:
        raise TechnicalManualBuildError(f"source hash mismatch for {manual.source.name}: {digest}")
    if not data:
        raise TechnicalManualBuildError(f"source is empty: {manual.source.name}")
    return data


def _read_existing_output(manual: ManualConfig, output_root: Path) -> bytes:
    """Read a packaged runtime output and trust only the configured SHA-256."""

    output_path = output_root / manual.output_filename
    try:
        data = output_path.read_bytes()
    except OSError as error:
        raise TechnicalManualBuildError(
            f"source {manual.source.name} and reusable output {manual.output_filename} are both unavailable"
        ) from error
    digest = _sha256(data)
    if digest != manual.sha256:
        raise TechnicalManualBuildError(f"reusable output hash mismatch for {manual.output_filename}: {digest}")
    return data


def _manifest_entry(manual: ManualConfig, data: bytes, project_root: Path) -> dict[str, str | int]:
    return {
        "id": manual.manual_id,
        "title": manual.title,
        "description": manual.description,
        "source": _source_provenance(manual, project_root),
        "version": manual.version,
        "url": f"/generated/technical-docs/{manual.output_filename}",
        "size_bytes": len(data),
        "sha256": _sha256(data),
        "output_path": manual.output_filename,
    }


def _source_provenance(manual: ManualConfig, project_root: Path) -> str:
    """Keep source provenance repository-relative while never emitting a machine path."""

    try:
        return manual.source.relative_to(project_root).as_posix()
    except ValueError:
        return manual.source.relative_to(project_root.parent).as_posix()


def _existing_output_digest(path: Path) -> str | None:
    try:
        return _sha256(path.read_bytes())
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project_root = args.project_root.resolve()
        config_path = _resolve_managed(str(args.config), project_root, project_root)
        version, output_root, manuals = _load_config(config_path, project_root)
        contents = [
            (
                manual,
                _read_validated_source(manual, output_root, reuse_existing=args.reuse_existing),
            )
            for manual in manuals
        ]
        if args.check:
            manifest_path = output_root / "manifest.json"
            try:
                existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise TechnicalManualBuildError(f"existing manifest is unavailable: {error}") from error
            expected = _build_manifest(version, contents, project_root)
            if existing_manifest != expected:
                raise TechnicalManualBuildError("existing manifest does not match configured sources")
            for manual, data in contents:
                digest = _existing_output_digest(output_root / manual.output_filename)
                if digest != _sha256(data):
                    raise TechnicalManualBuildError(f"existing output is stale: {manual.output_filename}")
        else:
            output_root.mkdir(parents=True, exist_ok=True)
            for manual, data in contents:
                output_path = output_root / manual.output_filename
                output_path.write_bytes(data)
            manifest = _build_manifest(version, contents, project_root)
            (output_root / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        print(
            json.dumps(
                {"status": "OK", "manuals": len(manuals), "mode": "check" if args.check else "build"},
                ensure_ascii=False,
            )
        )
        return 0
    except TechnicalManualBuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _build_manifest(
    version: str,
    contents: list[tuple[ManualConfig, bytes]],
    project_root: Path,
) -> dict[str, str | list[dict[str, str | int]]]:
    return {
        "version": version,
        "generated_at": version.split(".", 1)[0],
        "manuals": [_manifest_entry(manual, data, project_root) for manual, data in contents],
    }


if __name__ == "__main__":
    raise SystemExit(main())
