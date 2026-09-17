from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .domain.errors import AppError
from .bootstrap import create_workbench


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scienceresearch", description="离线科研工作台")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    sub.add_parser("health")
    week = sub.add_parser("week"); week.add_argument("week_start")
    context = sub.add_parser("context"); context.add_argument("type"); context.add_argument("name"); context.add_argument("problem"); context.add_argument("goal"); context.add_argument("--owner", default="author")
    workflow = sub.add_parser("workflow"); workflow.add_argument("context_id"); workflow.add_argument("wp_id")
    item = sub.add_parser("item"); item.add_argument("week_id"); item.add_argument("wp_id"); item.add_argument("title"); item.add_argument("deliverable"); item.add_argument("--relation")
    execute = sub.add_parser("execute"); execute.add_argument("item_id"); execute.add_argument("action"); execute.add_argument("inputs"); execute.add_argument("result"); execute.add_argument("output")
    evidence = sub.add_parser("evidence"); evidence.add_argument("item_id"); evidence.add_argument("name"); evidence.add_argument("kind"); evidence.add_argument("path")
    gate = sub.add_parser("gate"); gate.add_argument("item_id"); gate.add_argument("key", choices=("target", "standard", "deliverable", "evidence", "boundary", "next_step")); gate.add_argument("passed", choices=("true", "false"))
    complete = sub.add_parser("complete"); complete.add_argument("item_id")
    show_week = sub.add_parser("show-week"); show_week.add_argument("week_id")
    sub.add_parser("contexts")
    report = sub.add_parser("report"); report.add_argument("week_id"); report.add_argument("--output", type=Path)
    backup = sub.add_parser("backup"); backup.add_argument("target", type=Path)
    restore = sub.add_parser("restore"); restore.add_argument("source", type=Path)
    skill = sub.add_parser("skill-register"); skill.add_argument("manifest", type=Path)
    plan = sub.add_parser("skill-plan"); plan.add_argument("skill_id"); plan.add_argument("idempotency_key"); plan.add_argument("--inputs", default="{}")
    approve = sub.add_parser("skill-approve"); approve.add_argument("run_id"); approve.add_argument("--capabilities", nargs="*", default=[])
    run_skill = sub.add_parser("skill-run"); run_skill.add_argument("run_id"); run_skill.add_argument("--timeout", type=float, default=600)
    cancel_skill = sub.add_parser("skill-cancel"); cancel_skill.add_argument("run_id")
    recommend = sub.add_parser("recommend"); recommend.add_argument("item_id")
    decide = sub.add_parser("recommend-decide"); decide.add_argument("recommendation_id"); decide.add_argument("decision", choices=("Accepted", "Rejected"))
    card = sub.add_parser("card"); card.add_argument("week_id"); card.add_argument("--output", type=Path)
    doc_update = sub.add_parser("doc-update"); doc_update.add_argument("demand_id")
    sub.add_parser("governance")
    pptx = sub.add_parser("pptx"); pptx.add_argument("week_id"); pptx.add_argument("output", type=Path)
    discover = sub.add_parser("skill-discover"); discover.add_argument("url"); discover.add_argument("--allow", nargs="*", default=[]); discover.add_argument("--enable", action="store_true")
    assets = sub.add_parser("work-package-assets"); assets.add_argument("wp_id")
    artifact = sub.add_parser("template-artifact"); artifact.add_argument("wp_id"); artifact.add_argument("template_id"); artifact.add_argument("values"); artifact.add_argument("--artifact-ref")
    workflow_cmd = sub.add_parser("workflow-command"); workflow_cmd.add_argument("workflow_id"); workflow_cmd.add_argument("workflow_action"); workflow_cmd.add_argument("--expected-version", type=int); workflow_cmd.add_argument("--reason", default=""); workflow_cmd.add_argument("--mode")
    report_model = sub.add_parser("report-model"); report_model.add_argument("week_id")
    report_confirm = sub.add_parser("report-confirm"); report_confirm.add_argument("week_id"); report_confirm.add_argument("conclusion"); report_confirm.add_argument("--image")
    manual_step = sub.add_parser("manual-skill-step"); manual_step.add_argument("run_id"); manual_step.add_argument("step_no", type=int); manual_step.add_argument("--state", default="Completed"); manual_step.add_argument("--artifact-id"); manual_step.add_argument("--detail", default="")
    manual_control = sub.add_parser("manual-skill-control"); manual_control.add_argument("run_id"); manual_control.add_argument("control_action", choices=("pause", "resume", "cancel"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    app = create_workbench(args.data_dir)
    try:
        if args.command == "catalog": result = app.catalog()
        elif args.command == "health": result = app.health()
        elif args.command == "week": result = app.create_week(args.week_start)
        elif args.command == "context": result = app.create_context(args.type, args.name, args.problem, args.goal, args.owner)
        elif args.command == "workflow": result = app.start_workflow(args.context_id, args.wp_id)
        elif args.command == "item": result = app.add_week_item(args.week_id, args.wp_id, args.title, args.deliverable, args.relation)
        elif args.command == "execute": result = app.record_execution(args.item_id, args.action, args.inputs, args.result, args.output) or {"item_id": args.item_id, "status": "recorded"}
        elif args.command == "evidence":
            try:
                result = app.add_evidence(args.item_id, args.name, args.kind, args.path)
            except AppError as exc:
                if exc.code != "INVALID_EVIDENCE":
                    raise
                # CLI remains machine-readable for a staged/missing artifact;
                # strict Core/Web calls still reject it and no valid Evidence is stored.
                result = {"item_id": args.item_id, "name": args.name, "kind": args.kind,
                          "path": args.path, "status": "Invalid", "sha256": None,
                          "code": exc.code, "detail": exc.message}
        elif args.command == "gate": result = app.set_gate(args.item_id, args.key, args.passed == "true") or {"item_id": args.item_id, "gate": args.key, "passed": args.passed == "true"}
        elif args.command == "complete": result = app.complete_item(args.item_id)
        elif args.command == "show-week": result = app.week(args.week_id)
        elif args.command == "contexts": result = {"contexts": app.list_contexts()}
        elif args.command == "backup": result = {"path": str(app.backup(args.target))}
        elif args.command == "restore": result = {"path": str(app.restore(args.source))}
        elif args.command == "skill-register": result = app.register_skill(json.loads(args.manifest.read_text(encoding="utf-8")))
        elif args.command == "skill-plan": result = app.plan_skill(args.skill_id, json.loads(args.inputs), args.idempotency_key)
        elif args.command == "skill-approve": result = app.approve_skill_run(args.run_id, args.capabilities)
        elif args.command == "skill-run": result = app.execute_skill(args.run_id, args.timeout)
        elif args.command == "skill-cancel": result = app.cancel_skill_run(args.run_id)
        elif args.command == "recommend": result = {"recommendations": app.recommend(args.item_id)}
        elif args.command == "recommend-decide": result = app.decide_recommendation(args.recommendation_id, args.decision)
        elif args.command == "card":
            result = app.render_card(args.week_id)
            if args.output: args.output.write_text(result["html"], encoding="utf-8")
        elif args.command == "doc-update": result = app.advance_doc_update(args.demand_id)
        elif args.command == "governance": result = {"events": app.governance_events()}
        elif args.command == "pptx": result = {"path": str(app.render_pptx(args.week_id, args.output))}
        elif args.command == "skill-discover": result = app.discover_skill_metadata(args.url, args.allow, args.enable)
        elif args.command == "work-package-assets": result = app.work_package_assets(args.wp_id)
        elif args.command == "template-artifact": result = app.create_template_artifact(args.wp_id, args.template_id, json.loads(args.values) if args.values else None, args.artifact_ref)
        elif args.command == "workflow-command": result = app.apply_workflow_command(args.workflow_id, args.workflow_action, args.expected_version, reason=args.reason, mode=args.mode)
        elif args.command == "report-model": result = app.report_model(args.week_id)
        elif args.command == "report-confirm": result = app.confirm_report(args.week_id, args.conclusion, args.image)
        elif args.command == "manual-skill-step": result = app.advance_manual_skill(args.run_id, args.step_no, args.state, args.artifact_id, args.detail)
        elif args.command == "manual-skill-control": result = app.control_manual_skill(args.run_id, args.control_action)
        else:
            content = app.render_report(args.week_id)
            if args.output: args.output.write_text(content, encoding="utf-8")
            result = {"markdown": content, "output": str(args.output) if args.output else None}
    except AppError as exc:
        print(json.dumps({"code": exc.code, "detail": exc.message}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
