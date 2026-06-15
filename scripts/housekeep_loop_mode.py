#!/usr/bin/env python3
"""Housekeep Loop Mode skill artifacts without touching source truth."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT.parent / "_backups"
GENERATED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
GENERATED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".swp"}
GENERATED_FILE_NAMES = {".DS_Store"}


@dataclass(frozen=True)
class Candidate:
    path: Path
    reason: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": str(self.path),
            "reason": self.reason,
            "kind": self.kind,
        }


def is_generated(path: Path) -> bool:
    if path.is_dir() and path.name in GENERATED_DIR_NAMES:
        return True
    if path.is_file() and path.name in GENERATED_FILE_NAMES:
        return True
    return path.is_file() and path.suffix in GENERATED_SUFFIXES


def generated_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in ROOT.rglob("*"):
        if is_generated(path):
            candidates.append(Candidate(path, "generated-cache-or-temp", "generated"))
    return sorted(candidates, key=lambda item: str(item.path))


def parse_backup_time(path: Path) -> datetime | None:
    # Accept both compact timestamps and date-stamped backup names.
    for token in reversed(path.name.split("-")):
        if len(token) == 6 and token.isdigit():
            prefix = path.name[: -len(token)].rstrip("-")
            date = prefix.split("-")[-1]
            if len(date) == 8 and date.isdigit():
                try:
                    return datetime.strptime(date + token, "%Y%m%d%H%M%S").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    return None
    return None


def backup_candidates(keep_latest: int, max_age_days: int) -> list[Candidate]:
    if not BACKUP_ROOT.exists():
        return []
    dirs = [path for path in BACKUP_ROOT.iterdir() if path.is_dir() and path.name.startswith("loop-mode")]
    dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    keep = set(dirs[: max(keep_latest, 0)])
    now = datetime.now(timezone.utc).timestamp()
    max_age_seconds = max_age_days * 24 * 60 * 60
    candidates: list[Candidate] = []
    for path in dirs:
        if path in keep:
            continue
        is_empty = not any(path.iterdir())
        too_old = (now - path.stat().st_mtime) > max_age_seconds
        if is_empty:
            candidates.append(Candidate(path, "empty-backup-dir", "backup"))
        elif too_old:
            candidates.append(Candidate(path, f"older-than-{max_age_days}-days", "backup"))
    return sorted(candidates, key=lambda item: str(item.path))


def remove_candidate(candidate: Candidate) -> None:
    if candidate.path.is_dir():
        shutil.rmtree(candidate.path)
    else:
        candidate.path.unlink()


def run(args: argparse.Namespace) -> dict[str, object]:
    generated = generated_candidates()
    backups = backup_candidates(args.keep_backups, args.max_backup_age_days)

    removed: list[Candidate] = []
    if args.apply_generated:
        for candidate in sorted(generated, key=lambda item: len(item.path.parts), reverse=True):
            if not candidate.path.exists():
                continue
            remove_candidate(candidate)
            removed.append(candidate)

    if args.apply_backups:
        if not args.confirm_delete_backups:
            raise SystemExit("--apply-backups requires --confirm-delete-backups")
        for candidate in backups:
            if not candidate.path.exists():
                continue
            remove_candidate(candidate)
            removed.append(candidate)

    after_generated = generated_candidates()
    return {
        "status": "ok",
        "root": str(ROOT),
        "backup_root": str(BACKUP_ROOT),
        "apply_generated": args.apply_generated,
        "apply_backups": args.apply_backups,
        "generated_candidates": [item.as_dict() for item in generated],
        "backup_candidates": [item.as_dict() for item in backups],
        "removed": [item.as_dict() for item in removed],
        "remaining_generated_count": len(after_generated),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-generated", action="store_true")
    parser.add_argument("--apply-backups", action="store_true")
    parser.add_argument("--confirm-delete-backups", action="store_true")
    parser.add_argument("--keep-backups", type=int, default=5)
    parser.add_argument("--max-backup-age-days", type=int, default=14)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("LOOP_MODE_HOUSEKEEP_OK")
        print(f"generated_candidates={len(report['generated_candidates'])}")
        print(f"backup_candidates={len(report['backup_candidates'])}")
        print(f"removed={len(report['removed'])}")
        print(f"remaining_generated_count={report['remaining_generated_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
