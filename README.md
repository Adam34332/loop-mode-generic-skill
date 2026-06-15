# Loop Mode Generic Skill

通用版 Loop Mode Skill，已剥离私有项目 references，可单独分享给朋友使用。

Signature: adam.liu

## What It Does

Loop Mode is an execution pattern for agents:

1. Define the goal and success criteria.
2. Inspect live truth before acting.
3. Pick the narrowest useful entrypoint.
4. Make one atomic change or action.
5. Verify with a binary check.
6. Run an adversarial audit when available.
7. Decide whether to finish, continue, or stop for authorization.
8. Report what changed, what passed, and what risk remains.

It is meant for work where guessing, broad rewrites, duplicate reruns, or "looks done" answers are costly.

## Install

Copy this folder into your agent's skills directory, then restart or reload the agent if needed.

Example:

```bash
mkdir -p ~/.codex/skills
cp -R loop-mode-generic-skill ~/.codex/skills/loop-mode-generic
```

If your agent does not support skills, paste `SKILL.md` into the system or project instructions and keep `references/` available as linked context.

## Basic Usage

Use ordinary Loop Mode for one bounded task:

```text
用 loop 模式执行：
目标：修复导入脚本在空 CSV 上崩溃的问题
成功标准：新增/更新测试覆盖空 CSV，测试通过
约束：最小改动，不重构无关代码
禁止：删除已有数据文件
```

English prompt:

```text
Use Loop Mode:
Goal: fix the import script crash on empty CSV files.
Success criteria: a test covers empty CSV input and passes.
Constraints: minimal change, no unrelated refactor.
Forbidden: do not delete existing data files.
```

The agent should route through:

```text
Intake -> Inspect -> Route -> Execute -> Verify -> Adversarial Audit -> Decide -> Report
```

## Goal Mode

Use `/loop mode goal ...` when the objective may span multiple turns, long-running commands, multiple checkpoints, or auto-compact events.

```text
/loop mode goal 完成数据导入工具的稳定性修复，直到：
1. 空文件、缺列、重复行都有测试覆盖
2. 所有相关测试通过
3. README 更新使用限制
4. 没有未提交的目标内改动

约束：每轮只修一个根因；每轮写回状态；发现目标外破坏性动作先暂停。
禁止：删除用户数据；重写整个导入模块；跳过测试。
真源：当前仓库文件、测试输出、错误日志。
验证：pytest tests/test_import.py。
```

Goal Mode creates or updates a Long Goal Contract with:

- `definition_of_done`: exact evidence required to finish.
- `state_path`: where progress is written.
- `next_action`: one concrete atomic action.
- `progress_monitor`: what to check while work is not done.
- `monitor_window` / `monitor_interval` / `monitor_max_no_progress`: finite monitoring budget.
- `Compact Resume Anchor`: recovery block for compacted or resumed sessions.

Important behavior:

- A phase passing is only a checkpoint, not final completion.
- The agent should keep monitoring or advancing until `definition_of_done` is verified.
- It should stop only for completion, repeated no-progress blockage, destructive actions, permission/account/payment changes, invalid state, active lock conflict, or explicit user pause.

## Common Prompt Patterns

Bug fix:

```text
用 loop 模式修复：[问题]
成功标准：[测试/命令/readback]
约束：最小改动，根因修复
禁止：用全链路重跑证明局部修复
```

System inspection:

```text
用 loop 模式做自检：
目标：扫描 [系统/仓库] 的真实问题
成功标准：输出问题清单、证据、优先级；只修已授权且能验证的问题
禁止：跳过 Inspect 直接修改
```

Long-running goal:

```text
/loop mode goal 完成 [最终目标]，直到 [可验证停止条件]。
约束：[必须遵守]
禁止：[绝对不能做]
真源：[必须先读的文件/DB/日志/API]
验证：[证明完成的命令/报告/状态]
```

## Validation

Run these before sharing or after editing the skill:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_loop_mode_goal_contract.py
PYTHONPYCACHEPREFIX=/tmp/loop-mode-pycache python3 -m py_compile scripts/*.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/housekeep_loop_mode.py --json
```

## License

MIT License. See `LICENSE`.

## Files

- `SKILL.md`：主入口和通用不变量。
- `references/`：长期目标、输出模板、五类场景模板。
- `scripts/`：合同校验、长期目标状态校验、自清理脚本。

## Quick Check

```bash
cd loop-mode-generic-skill
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_loop_mode_goal_contract.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/housekeep_loop_mode.py --json
```
