#!/usr/bin/env python3
"""Validate a generated Long Goal Contract markdown state file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


VALID_STATUSES = {"active", "blocked", "complete", "paused"}
VALID_AUDIT_STATUSES = {"pending", "pass", "fail", "needs_fix", "audit_unavailable"}
FORBIDDEN_AUDITOR_TOKENS = {
    "gemini",
    "hermes",
    "glm",
    "qwen",
    "zhipu",
    "openai api",
    "generic model",
    "other model",
    "other models",
    "通用模型",
    "其他模型",
}
REQUIRED_TOP_FIELDS = [
    "status",
    "created_at",
    "updated_at",
    "owner_tool",
    "state_path",
    "state_path_aliases",
    "lock_path",
    "lock_path_aliases",
    "goal_revision",
]
REQUIRED_SECTIONS = [
    "Goal Snapshot",
    "Scope",
    "Authority Sources",
    "Execution Loop",
    "Runner Lock",
    "Adversarial Audit Gate",
    "Progress Monitor",
    "Progress Log",
    "Compact Resume Anchor",
]
REQUIRED_ANCHOR_FIELDS = [
    "state_path",
    "state_path_aliases",
    "lock_path",
    "lock_path_aliases",
    "goal_id",
    "status",
    "goal_snapshot",
    "current_checkpoint",
    "next_action",
    "monitor_next_probe",
    "verification_required",
    "adversarial_audit_required",
    "adversarial_audit_status",
    "stop_if",
]
REQUIRED_AUDIT_FIELDS = [
    "auditor",
    "audit_trigger",
    "audit_inputs",
    "audit_scope",
    "pass_condition",
    "fail_action",
    "unavailable_action",
    "last_audit_status",
]
REQUIRED_MONITOR_FIELDS = [
    "phase_complete_is_not_done",
    "monitor_backend",
    "monitor_task_id",
    "monitor_target",
    "monitor_event_sink",
    "monitor_window",
    "monitor_cadence",
    "monitor_interval",
    "monitor_max_no_progress",
    "monitor_max_runtime",
    "monitor_on_timeout",
    "monitor_next_probe",
    "monitor_stop_when",
    "monitor_escalate_when",
    "monitor_fallback",
]
VAGUE_NEXT_ACTIONS = {
    "继续",
    "继续推进",
    "继续优化",
    "继续执行",
    "下一步",
    "待定",
    "tbd",
    "todo",
    "n/a",
}
VAGUE_MONITOR_PROBES = {
    "继续",
    "继续观察",
    "继续监控",
    "保持监控",
    "等待",
    "等待完成",
    "等完成",
    "观察进度",
    "monitor",
    "wait",
    "wait for completion",
    "tbd",
    "todo",
    "n/a",
}
UNBOUNDED_VALUES = {
    "infinite",
    "forever",
    "unbounded",
    "no limit",
    "none",
    "never",
    "无限",
    "永久",
    "无上限",
    "不限",
    "一直等",
    "一直监控",
}


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"state file missing: {path}")
    return path.read_text(encoding="utf-8")


def top_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## "):
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def section_names(text: str) -> set[str]:
    return {m.group(1).strip() for m in re.finditer(r"^##\s+(.+)$", text, re.M)}


def anchor_block(text: str) -> dict[str, str]:
    match = re.search(
        r"LONG_GOAL_RESUME\s*\n(?P<body>.*?)(?:\n```|\Z)",
        text,
        re.S,
    )
    if not match:
        raise AssertionError("missing LONG_GOAL_RESUME block")
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        match_line = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line.strip())
        if match_line:
            fields[match_line.group(1)] = match_line.group(2).strip()
    return fields


def section_fields(text: str, section: str) -> dict[str, str]:
    match = re.search(
        rf"^##\s+{re.escape(section)}\s*\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.S | re.M,
    )
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        match_line = re.match(r"^-\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line.strip())
        if match_line:
            fields[match_line.group(1)] = match_line.group(2).strip()
    return fields


def looks_placeholder(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped in {"...", "TODO", "TBD", "待定"}:
        return True
    return bool(re.fullmatch(r"[\[<].*[\]>]", stripped))


def check_required(mapping: dict[str, str], required: list[str], label: str) -> None:
    missing = [key for key in required if key not in mapping or looks_placeholder(mapping[key])]
    if missing:
        raise AssertionError(f"{label} missing or placeholder: {', '.join(missing)}")


def check_next_action(value: str, status: str) -> None:
    if status == "complete":
        return
    normalized = re.sub(r"\s+", "", value.lower())
    if looks_placeholder(value) or normalized in VAGUE_NEXT_ACTIONS:
        raise AssertionError(f"next_action is not atomic: {value!r}")
    if len(value) < 6:
        raise AssertionError(f"next_action too short to verify: {value!r}")


def check_monitor_probe(value: str, status: str) -> None:
    if status == "complete":
        return
    normalized = re.sub(r"\s+", "", value.lower())
    vague = {re.sub(r"\s+", "", item.lower()) for item in VAGUE_MONITOR_PROBES}
    if looks_placeholder(value) or normalized in vague:
        raise AssertionError(f"monitor_next_probe is not concrete: {value!r}")
    if len(value) < 8:
        raise AssertionError(f"monitor_next_probe too short to verify: {value!r}")


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def reject_unbounded(value: str, label: str) -> None:
    norm = normalized(value)
    compact = re.sub(r"\s+", "", norm)
    unbounded = {re.sub(r"\s+", "", item.lower()) for item in UNBOUNDED_VALUES}
    if not norm or compact in unbounded or looks_placeholder(value):
        raise AssertionError(f"{label} must be finite and explicit: {value!r}")


def parse_duration_seconds(value: str) -> int | None:
    reject_unbounded(value, "duration")
    match = re.fullmatch(
        r"(\d+)\s*(s|sec|secs|second|seconds|秒|m|min|mins|minute|minutes|分|分钟|h|hr|hrs|hour|hours|小时)",
        value.strip().lower(),
    )
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit in {"s", "sec", "secs", "second", "seconds", "秒"}:
        return amount
    if unit in {"m", "min", "mins", "minute", "minutes", "分", "分钟"}:
        return amount * 60
    return amount * 3600


def check_duration(value: str, label: str, *, min_seconds: int, max_seconds: int) -> None:
    seconds = parse_duration_seconds(value)
    if seconds is None:
        raise AssertionError(f"{label} must be a finite duration like 30s/5m/2h: {value!r}")
    if seconds < min_seconds:
        raise AssertionError(f"{label} too small; avoid busy polling: {value!r}")
    if seconds > max_seconds:
        raise AssertionError(f"{label} too large for one monitor lease: {value!r}")


def check_interval(value: str) -> None:
    reject_unbounded(value, "monitor_interval")
    if normalized(value) in {"after each event", "after each command", "event-driven", "command-driven"}:
        return
    check_duration(value, "monitor_interval", min_seconds=5, max_seconds=3600)


def check_positive_int(value: str, label: str) -> None:
    reject_unbounded(value, label)
    if not re.fullmatch(r"\d+", value.strip()):
        raise AssertionError(f"{label} must be a positive integer: {value!r}")
    if int(value.strip()) <= 0:
        raise AssertionError(f"{label} must be positive: {value!r}")


def check_timeout_action(value: str) -> None:
    reject_unbounded(value, "monitor_on_timeout")
    required = {
        "writeback",
        "handoff",
        "blocked",
        "paused",
        "active",
        "写回",
        "交接",
        "阻塞",
        "暂停",
        "状态",
    }
    norm = normalized(value)
    if not any(token in norm for token in required):
        raise AssertionError(
            "monitor_on_timeout must describe writeback/handoff/block/pause action"
        )


def check_progress_monitor(monitor: dict[str, str], status: str) -> None:
    if status == "complete":
        return
    check_required(monitor, REQUIRED_MONITOR_FIELDS, "progress monitor")
    phase_flag = monitor["phase_complete_is_not_done"].strip().lower()
    if phase_flag not in {"true", "yes", "是", "1"}:
        raise AssertionError("phase_complete_is_not_done must be true for active goals")
    check_duration(monitor["monitor_window"], "monitor_window", min_seconds=60, max_seconds=24 * 3600)
    check_interval(monitor["monitor_interval"])
    check_positive_int(monitor["monitor_max_no_progress"], "monitor_max_no_progress")
    check_duration(monitor["monitor_max_runtime"], "monitor_max_runtime", min_seconds=60, max_seconds=24 * 3600)
    check_timeout_action(monitor["monitor_on_timeout"])
    check_monitor_probe(monitor["monitor_next_probe"], status)


def check_audit_gate(audit: dict[str, str], anchor: dict[str, str], status: str) -> None:
    check_required(audit, REQUIRED_AUDIT_FIELDS, "adversarial audit gate")
    auditor = normalized(audit["auditor"])
    if any(token in auditor for token in FORBIDDEN_AUDITOR_TOKENS):
        raise AssertionError("auditor must not use non-native models or agents")
    native_subagent = (
        "current-runtime-native-subagent" in auditor
        or "current tool native subagent" in auditor
        or "current-tool-native-subagent" in auditor
        or "same-tool-native-subagent" in auditor
        or "native subagent" in auditor
        or "原生子agent" in auditor
        or "当前工具子agent" in auditor
        or (
            ("当前运行环境" in auditor or "当前工具" in auditor)
            and ("原生" in auditor or "子agent" in auditor)
        )
    )
    if not native_subagent and auditor != "audit_unavailable":
        raise AssertionError("auditor must be current-runtime native subagent or audit_unavailable")
    if "fallback" in auditor or "backup" in auditor or "optional" in auditor:
        raise AssertionError("auditor must not declare cross-tool fallback/backup/optional routing")
    if (
        ("other agent" in auditor and "no other agent" not in auditor)
        or ("其他 agent" in auditor and "禁止其他 agent" not in auditor)
        or ("其他agent" in auditor and "禁止其他agent" not in auditor)
    ):
        raise AssertionError("auditor must not use other agents")
    required_flag = anchor["adversarial_audit_required"].strip().lower()
    if required_flag not in {"true", "yes", "是", "1"}:
        raise AssertionError("adversarial_audit_required must be true")
    audit_status = anchor["adversarial_audit_status"].strip()
    if audit_status not in VALID_AUDIT_STATUSES:
        raise AssertionError(f"invalid adversarial_audit_status: {audit_status}")
    if audit["last_audit_status"].strip() != audit_status:
        raise AssertionError("audit gate last_audit_status does not match resume anchor")
    if status == "complete" and audit_status != "pass":
        raise AssertionError("complete goals require adversarial_audit_status: pass")
    if status == "active" and audit_status in {"fail", "needs_fix"}:
        fail_action = audit["fail_action"]
        if looks_placeholder(fail_action) or len(fail_action) < 8:
            raise AssertionError("failed audit requires concrete fail_action")


def split_aliases(value: str) -> list[Path]:
    if value.lower() in {"none", "无", "n/a"}:
        return []
    parts = [part.strip() for part in re.split(r"[,;，；]", value) if part.strip()]
    return [Path(part).expanduser() for part in parts]


def path_matches_current(path: Path, current: Path) -> bool:
    try:
        return path.resolve() == current.resolve()
    except OSError:
        return path.absolute() == current.absolute()


def validate(path: Path) -> None:
    text = read(path)
    fields = top_fields(text)
    check_required(fields, REQUIRED_TOP_FIELDS, "top fields")

    status = fields["status"]
    if status not in VALID_STATUSES:
        raise AssertionError(f"invalid status: {status}")

    state_path = Path(fields["state_path"])
    state_path_aliases = split_aliases(fields["state_path_aliases"])
    lock_path = Path(fields["lock_path"])
    lock_path_aliases = split_aliases(fields["lock_path_aliases"])
    if not state_path.is_absolute():
        raise AssertionError("state_path must be absolute")
    for alias in state_path_aliases:
        if not alias.is_absolute():
            raise AssertionError(f"state_path_aliases must be absolute: {alias}")
    if not lock_path.is_absolute():
        raise AssertionError("lock_path must be absolute")
    for alias in lock_path_aliases:
        if not alias.is_absolute():
            raise AssertionError(f"lock_path_aliases must be absolute: {alias}")
    if not any(path_matches_current(candidate, path) for candidate in [state_path, *state_path_aliases]):
        raise AssertionError(
            f"state_path/state_path_aliases do not match file: {state_path} != {path}"
        )

    sections = section_names(text)
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing_sections:
        raise AssertionError(f"missing sections: {', '.join(missing_sections)}")

    check_progress_monitor(section_fields(text, "Progress Monitor"), status)

    anchor = anchor_block(text)
    check_required(anchor, REQUIRED_ANCHOR_FIELDS, "resume anchor")
    check_audit_gate(section_fields(text, "Adversarial Audit Gate"), anchor, status)
    if anchor["state_path"] != fields["state_path"]:
        raise AssertionError("anchor state_path does not match top state_path")
    if anchor["state_path_aliases"] != fields["state_path_aliases"]:
        raise AssertionError("anchor state_path_aliases does not match top state_path_aliases")
    if anchor["lock_path"] != fields["lock_path"]:
        raise AssertionError("anchor lock_path does not match top lock_path")
    if anchor["lock_path_aliases"] != fields["lock_path_aliases"]:
        raise AssertionError("anchor lock_path_aliases does not match top lock_path_aliases")
    if anchor["status"] != status:
        raise AssertionError("anchor status does not match top status")
    check_next_action(anchor["next_action"], status)
    check_monitor_probe(anchor["monitor_next_probe"], status)

    stop_if = anchor["stop_if"]
    for token in ["done", "active-lock", "state-invalid"]:
        if token not in stop_if:
            raise AssertionError(f"stop_if missing {token!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_file", type=Path)
    args = parser.parse_args()
    validate(args.state_file)
    print("LONG_GOAL_STATE_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"LONG_GOAL_STATE_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
