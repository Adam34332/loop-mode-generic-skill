#!/usr/bin/env python3
"""Validate generic Loop Mode skill wiring."""

from __future__ import annotations

import re
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = {
    "SKILL.md": [
        "/loop mode goal",
        "long-goal.md",
        "冒号只是可选",
        "goal(\\s|:|$)",
        "长期目标/追求目标",
        "精确入口优先",
        "只靠聊天上下文记目标",
        "持续监控",
        "阶段性完成只是 checkpoint",
        "Adversarial Audit",
        "外部找茬审计",
        "audit_unavailable",
        "当前运行环境自己的原生子agent",
    ],
    "references/long-goal.md": [
        "Long Goal Contract",
        "Goal Snapshot",
        "Adversarial Audit Gate",
        "Progress Monitor",
        "Compact Resume Anchor",
        "LONG_GOAL_RESUME",
        "auto-compact 防丢规则",
        "持续监控协议",
        "phase_complete_is_not_done",
        "monitor_backend",
        "monitor_next_probe",
        "monitor_budget",
        "monitor_window",
        "monitor_interval",
        "monitor_max_runtime",
        "monitor_max_no_progress",
        "monitor_on_timeout",
        "adversarial_audit_required",
        "adversarial_audit_status",
        "当前运行环境的原生找茬审计子agent",
        "无限",
        "session",
        "checkpoint",
        "并发与锁",
        "应急恢复",
        "自动停止条件",
        "next_action",
        "state_path",
        "state_path_aliases",
        "lock_path",
        "lock_path_aliases",
        "冒号可选",
    ],
    "references/output-formats.md": [
        "Long Goal Contract",
        "Progress Monitor",
        "Compact Resume Anchor",
        "LONG_GOAL_RESUME",
        "Runner Lock",
        "phase_complete_is_not_done",
        "monitor_backend",
        "monitor_task_id",
        "monitor_event_sink",
        "monitor_fallback",
        "monitor_window",
        "monitor_interval",
        "monitor_max_runtime",
        "monitor_max_no_progress",
        "monitor_on_timeout",
        "monitor_next_probe",
        "Adversarial Audit Gate",
        "adversarial_audit_required",
        "adversarial_audit_status",
        "current-runtime-native-subagent",
        "state_path_aliases",
        "lock_path_aliases",
        "state-invalid",
        "每轮更新 Goal Snapshot、Progress Log、Progress Monitor",
        "目标内授权",
        "paid-or-account-change",
    ],
    "references/scene-2-writing.md": [
        "内容续作",
        "长期 goal",
        "目标内可恢复问题",
    ],
    "references/scene-4-guard.md": [
        "长期守护",
        "同一长期 goal",
        "目标内可恢复阻塞当成最终交付",
    ],
    "scripts/validate_long_goal_state.py": [
        "LONG_GOAL_STATE_OK",
        "LONG_GOAL_RESUME",
        "Progress Monitor",
        "monitor_backend",
        "monitor_event_sink",
        "monitor_fallback",
        "monitor_window",
        "monitor_interval",
        "monitor_max_runtime",
        "monitor_max_no_progress",
        "monitor_on_timeout",
        "UNBOUNDED_VALUES",
        "monitor_next_probe",
        "Adversarial Audit Gate",
        "adversarial_audit_required",
        "adversarial_audit_status",
        "current-runtime native subagent",
        "non-native",
        "other model",
        "phase_complete_is_not_done",
        "state_path_aliases",
        "lock_path_aliases",
        "active-lock",
        "state-invalid",
    ],
    "scripts/housekeep_loop_mode.py": [
        "LOOP_MODE_HOUSEKEEP_OK",
        "apply-generated",
        "confirm-delete-backups",
        "remaining_generated_count",
    ],
}


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def check_required_strings() -> None:
    for rel, needles in REQUIRED.items():
        text = read(ROOT / rel)
        missing = [needle for needle in needles if needle not in text]
        if missing:
            raise AssertionError(f"{rel} missing: {missing}")


def check_forbidden_terms() -> None:
    raw_terms = os.environ.get("LOOP_MODE_FORBIDDEN_TERMS", "")
    forbidden_terms = [term.strip() for term in raw_terms.split(",") if term.strip()]
    if not forbidden_terms:
        return
    offenders: list[str] = []
    for path in [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md")), *sorted((ROOT / "scripts").glob("*.py"))]:
        text = read(path)
        for term in forbidden_terms:
            if term in text:
                offenders.append(f"{path.relative_to(ROOT)} contains {term!r}")
    if offenders:
        raise AssertionError("project-specific terms remain: " + "; ".join(offenders))


def check_links() -> None:
    for path in [
        ROOT / "SKILL.md",
        *sorted((ROOT / "references").glob("*.md")),
        *sorted((ROOT / "scripts").glob("*.py")),
    ]:
        text = read(path)
        for target in re.findall(r"\]\(([^)]+\.md)\)", text):
            if target.startswith("http"):
                continue
            resolved = ROOT / target if target.startswith("references/") else path.parent / target
            if not resolved.exists():
                raise AssertionError(
                    f"broken link in {path.relative_to(ROOT)}: {target}"
                )


def check_code_fences() -> None:
    fence_re = re.compile(r"^(`{3,}|~{3,})")
    for path in [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md"))]:
        open_fence: tuple[str, int, int] | None = None
        for lineno, line in enumerate(read(path).splitlines(), 1):
            match = fence_re.match(line)
            if not match:
                continue
            fence = match.group(1)
            marker, length = fence[0], len(fence)
            if open_fence is None:
                open_fence = (marker, length, lineno)
                continue
            open_marker, open_length, _ = open_fence
            if marker == open_marker and length >= open_length:
                open_fence = None
        if open_fence is not None:
            _, _, start = open_fence
            raise AssertionError(
                f"unclosed code fence in {path.relative_to(ROOT)} starting line {start}"
            )


def check_no_generated_artifacts() -> None:
    generated: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}:
            generated.append(str(path.relative_to(ROOT)))
        elif path.is_file() and (path.suffix in {".pyc", ".pyo"} or path.name == ".DS_Store"):
            generated.append(str(path.relative_to(ROOT)))
    if generated:
        raise AssertionError(
            "generated artifacts found; run scripts/housekeep_loop_mode.py --apply-generated: "
            + ", ".join(sorted(generated))
        )


def main() -> int:
    check_required_strings()
    check_forbidden_terms()
    check_links()
    check_code_fences()
    check_no_generated_artifacts()
    print("LOOP_MODE_GOAL_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"LOOP_MODE_GOAL_CONTRACT_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
