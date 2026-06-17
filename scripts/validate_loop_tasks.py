#!/usr/bin/env python3
"""Validate a Loop Mode coding task board."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


VALID_STATUSES = {
    "todo",
    "claimed",
    "in_progress",
    "verify_pending",
    "audit_pending",
    "passed",
    "blocked",
}
VALID_VERIFICATION_RESULTS = {"pending", "pass", "fail"}
VALID_AUDIT_STATUSES = {"pending", "pass", "fail", "needs_fix", "audit_unavailable"}
IMMUTABLE_TASK_FIELDS = {
    "id",
    "title",
    "description",
    "description_hash",
    "steps",
    "steps_hash",
    "depends_on",
    "acceptance",
    "write_scope",
    "priority",
    "required",
}
REQUIRED_BLOCKER_FIELDS = [
    "blocked_at",
    "blocked_by",
    "evidence",
    "human_action_required",
    "next_probe",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"task board missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError("task board root must be an object")
    return data


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_steps(steps: list[Any]) -> str:
    return json.dumps(steps, ensure_ascii=False, separators=(",", ":"))


def normalize_hash(value: Any) -> str:
    if not isinstance(value, str):
        raise AssertionError("hash value must be a string")
    return value.removeprefix("sha256:")


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AssertionError(f"{label} must be a list")
    return value


def check_hash(task: dict[str, Any], field: str, hash_field: str) -> None:
    raw = task.get(field)
    expected = normalize_hash(task.get(hash_field))
    if field == "steps":
        if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
            raise AssertionError(f"{task.get('id')}: steps must be non-empty strings")
        actual = sha256_text(canonical_steps(raw))
    else:
        if not isinstance(raw, str) or not raw:
            raise AssertionError(f"{task.get('id')}: {field} must be a non-empty string")
        actual = sha256_text(raw)
    if actual != expected:
        raise AssertionError(f"{task.get('id')}: {hash_field} does not match {field}")


def check_top_fields(data: dict[str, Any]) -> None:
    for key in ["project_id", "goal_id"]:
        if not isinstance(data.get(key), str) or not data[key]:
            raise AssertionError(f"{key} must be a non-empty string")
    for key in ["revision", "planning_revision"]:
        if not isinstance(data.get(key), int) or data[key] < 1:
            raise AssertionError(f"{key} must be a positive integer")
    commit_policy = require_object(data.get("commit_policy"), "commit_policy")
    if commit_policy.get("commit_after_verify_and_audit") is not True:
        raise AssertionError("commit_policy.commit_after_verify_and_audit must be true")
    if commit_policy.get("require_clean_status_for_goal_complete") is not True:
        raise AssertionError("commit_policy.require_clean_status_for_goal_complete must be true")
    require_list(data.get("tasks"), "tasks")


def check_blocker(task_id: str, blocker: Any) -> None:
    blocker_obj = require_object(blocker, f"{task_id}: blocker")
    for key in REQUIRED_BLOCKER_FIELDS:
        if key not in blocker_obj:
            raise AssertionError(f"{task_id}: blocker missing {key}")
    if not require_list(blocker_obj["evidence"], f"{task_id}: blocker.evidence"):
        raise AssertionError(f"{task_id}: blocker.evidence must not be empty")
    if not require_list(
        blocker_obj["human_action_required"],
        f"{task_id}: blocker.human_action_required",
    ):
        raise AssertionError(f"{task_id}: blocker.human_action_required must not be empty")
    if not isinstance(blocker_obj["next_probe"], str) or len(blocker_obj["next_probe"]) < 8:
        raise AssertionError(f"{task_id}: blocker.next_probe must be concrete")


def task_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tasks = require_list(data.get("tasks"), "tasks")
    result: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_obj = require_object(task, "task")
        task_id = task_obj.get("id")
        if task_id in result:
            raise AssertionError(f"duplicate task id: {task_id}")
        result[str(task_id)] = task_obj
    return result


def check_task(task: dict[str, Any], task_ids: set[str]) -> None:
    task_id = task.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise AssertionError("task id must be a non-empty string")
    for key in ["title", "description", "description_hash", "steps", "steps_hash"]:
        if key not in task:
            raise AssertionError(f"{task_id}: missing {key}")
    check_hash(task, "description", "description_hash")
    check_hash(task, "steps", "steps_hash")

    status = task.get("status")
    if status not in VALID_STATUSES:
        raise AssertionError(f"{task_id}: invalid status {status!r}")
    for dep in task.get("depends_on", []):
        if dep not in task_ids:
            raise AssertionError(f"{task_id}: unknown dependency {dep!r}")

    verification = require_object(task.get("verification"), f"{task_id}: verification")
    audit = require_object(task.get("audit"), f"{task_id}: audit")
    if verification.get("result") not in VALID_VERIFICATION_RESULTS:
        raise AssertionError(f"{task_id}: invalid verification.result")
    if audit.get("status") not in VALID_AUDIT_STATUSES:
        raise AssertionError(f"{task_id}: invalid audit.status")
    evidence = require_list(verification.get("evidence"), f"{task_id}: verification.evidence")

    if status == "passed":
        if verification.get("result") != "pass":
            raise AssertionError(f"{task_id}: passed task requires verification.result=pass")
        if audit.get("required") is not True:
            raise AssertionError(f"{task_id}: passed task requires audit.required=true")
        if audit.get("status") != "pass":
            raise AssertionError(f"{task_id}: passed task requires audit.status=pass")
        if not evidence:
            raise AssertionError(f"{task_id}: passed task requires verification evidence")
    elif status == "audit_pending" and verification.get("result") != "pass":
        raise AssertionError(f"{task_id}: audit_pending requires verification.result=pass")
    elif status == "blocked":
        check_blocker(task_id, task.get("blocker"))

    if "passes" in task:
        if not isinstance(task["passes"], bool):
            raise AssertionError(f"{task_id}: passes must be boolean")
        if task["passes"] != (status == "passed"):
            raise AssertionError(f"{task_id}: passes must mirror status == passed")


def check_previous(current: dict[str, Any], previous: dict[str, Any]) -> None:
    current_tasks = task_map(current)
    previous_tasks = task_map(previous)
    planning_changed = current.get("planning_revision") != previous.get("planning_revision")
    if planning_changed:
        return
    if previous.get("commit_policy") != current.get("commit_policy"):
        raise AssertionError("commit_policy changed without planning_revision change")
    if set(current_tasks) != set(previous_tasks):
        raise AssertionError("task ids changed without planning_revision change")
    for task_id, previous_task in previous_tasks.items():
        current_task = current_tasks[task_id]
        for field in IMMUTABLE_TASK_FIELDS:
            if previous_task.get(field) != current_task.get(field):
                raise AssertionError(
                    f"{task_id}: immutable field changed without planning_revision: {field}"
                )
        previous_verification = require_object(
            previous_task.get("verification"),
            f"{task_id}: previous verification",
        )
        current_verification = require_object(
            current_task.get("verification"),
            f"{task_id}: current verification",
        )
        for field in ["required", "commands"]:
            if previous_verification.get(field) != current_verification.get(field):
                raise AssertionError(
                    f"{task_id}: verification.{field} changed without planning_revision"
                )
        previous_audit = require_object(previous_task.get("audit"), f"{task_id}: previous audit")
        current_audit = require_object(current_task.get("audit"), f"{task_id}: current audit")
        if previous_audit.get("required") != current_audit.get("required"):
            raise AssertionError(f"{task_id}: audit.required changed without planning_revision")


def validate_task_board(path: Path, previous: Path | None = None) -> dict[str, Any]:
    data = load_json(path)
    check_top_fields(data)
    tasks = task_map(data)
    if not tasks:
        raise AssertionError("tasks must not be empty")
    for task in tasks.values():
        check_task(task, set(tasks))
    if previous is not None:
        check_previous(data, load_json(previous))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_board", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    validate_task_board(args.task_board, args.previous)
    print("LOOP_TASKS_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"LOOP_TASKS_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
