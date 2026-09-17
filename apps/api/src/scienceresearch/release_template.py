from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import ResearchWorkbench


def _write_safe_release_operations_config(data_dir: Path, *, updated_by: str) -> None:
    """Remove machine-local paths and credentials from a generated release config."""
    config_path = data_dir / "operations.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["business_root"] = ""
    config["model_profile"] = {
        "endpoint": "",
        "model": "",
        "timeout_seconds": 60,
        "enabled": False,
        "api_key_dpapi_b64": "",
    }
    config["connection_check"] = {}
    config["updated_by"] = updated_by
    config["history"] = [
        {
            "revision": config["revision"],
            "changed_at": config["updated_at"],
            "changed_by": updated_by,
            "fields": ["upload_limits", "model_profile", "business_root"],
        }
    ]
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def create_blank_release_candidate(database_path: Path, catalog_source: Path | None = None) -> dict[str, Any]:
    """Initialize a runnable, data-free legacy SQLite release candidate.

    The database is created only through the application's normal schema and
    migration path.  Callers own conflict handling and final-path publication;
    this function deliberately refuses an existing target.
    """
    if database_path.exists():
        raise FileExistsError(f"release candidate database already exists: {database_path.name}")

    data_dir = database_path.parent
    ResearchWorkbench(
        database_path,
        data_dir / "artifacts",
        catalog_source=catalog_source,
        bootstrap_dir=data_dir,
    )
    _write_safe_release_operations_config(data_dir, updated_by="release-candidate")
    return {"database_file": database_path.name, "business_record_count": 0}


def create_release_template(data_dir: Path, catalog_source: Path | None = None) -> dict[str, Any]:
    """Create a safe, runnable release dataset with representative example records.

    The caller must supply a new or intentionally reset directory.  The template
    is built through the application's public domain operations so its SQLite
    schema and attachment layout remain compatible with normal local use.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    app = ResearchWorkbench(
        data_dir / "scienceresearch.db",
        data_dir / "artifacts",
        catalog_source=catalog_source,
        bootstrap_dir=data_dir,
    )
    if app.list_contexts():
        raise ValueError("release template data directory already contains contexts")

    context = app.create_context(
        "topic",
        "示例课题：实验方案与证据闭环",
        "用一份脱敏示例展示从工作包到成效卡和附件预览的完整流程。",
        "建立可复核的研究方案、执行记录与成果证据。",
        owner="示例用户",
    )
    workflows = app.workflows_for_context(context["id"])
    by_work_package = {workflow["work_package_id"]: workflow for workflow in workflows}
    important_card = app.create_achievement_card(
        context["id"],
        by_work_package["WP-001"]["id"],
        "2026-09-04",
        "示例：完成研究问题与验证边界梳理",
        "这是可删除、可编辑、可标记重点的演示成效卡，不包含任何真实业务数据。",
        actor="示例用户",
        is_important=True,
    )
    app.add_achievement_attachment(
        important_card["id"],
        "示例研究记录.md",
        "# 示例研究记录\n\n- 目标：验证完整工作流。\n- 结论：此文件仅用于发布模板预览。\n".encode("utf-8"),
    )
    app.create_achievement_card(
        context["id"],
        by_work_package["WP-002"]["id"],
        "2026-09-04",
        "示例：待补充的验证计划",
        "此普通成效卡用于演示筛选、展开和新增入口。",
        actor="示例用户",
    )

    _write_safe_release_operations_config(data_dir, updated_by="release-template")

    return {
        "context_id": context["id"],
        "workflow_count": len(workflows),
        "achievement_card_count": 2,
        "attachment_count": 1,
    }
