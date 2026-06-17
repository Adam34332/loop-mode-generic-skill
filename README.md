# Loop Mode Generic Skill

通用版 Loop Mode Skill，私有项目可在 references中配置，通用型Skill。

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

## Supported Environments

This package is plain Markdown plus small Python validation scripts. It works best in coding agents that can read project files, run commands, and keep task state.

| Environment | How to Use | Notes |
|-------------|------------|-------|
| Codex CLI / Codex-style agents | Install the folder as a skill, or paste `SKILL.md` into project instructions. | Best fit: native skill loading can route to `references/` on demand. |
| Claude Code | Put the Loop Mode rules in `CLAUDE.md`, project instructions, or a custom skill/memory folder if your setup supports it. | For `/loop mode goal`, ask Claude Code to write the Long Goal Contract into the repo, for example `.loop-goals/<goal-id>.md`. |
| VS Code agent extensions | Add `SKILL.md` to the workspace instruction file used by your extension. | Works with tools such as Copilot-style agents, Continue, Cursor, or similar IDE agents when they can read files and run terminal commands. |
| Zed / Zcode-style coding agents | Add `SKILL.md` as project context or agent instructions. | If the tool has no native skill system, keep `references/` in the repo and tell the agent to load the relevant reference file. |
| Generic ChatGPT / Claude / web chat | Paste the relevant sections of `SKILL.md` into the conversation. | Goal Mode still works conceptually, but the user or agent must manually maintain the state file. |
| Automation runners / CI agents | Vendor this folder into the repo and call the Python validation scripts in CI. | Useful for checking that edited Loop Mode contracts and scripts remain coherent. |

Minimum capability required:

- Read local project files.
- Follow `SKILL.md` as persistent instructions.
- Run shell commands for validation, or at least report when command execution is unavailable.
- For Goal Mode, write and reread a state file such as `.loop-goals/<goal-id>.md`.

If an environment cannot persist files, use ordinary Loop Mode rather than Goal Mode, or paste the `Compact Resume Anchor` into the next session manually.

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

## Long-Running Coding Projects

For coding projects that may take many turns or multiple agent sessions, use a lightweight task board beside the Long Goal Contract:

```text
1. Create examples/coding-project/loop-tasks.json-style tasks from the product goal.
2. Keep loop-progress.md as an append-only handoff log.
3. Use a bootstrap check to prove the local app/test environment is ready.
4. Work one task at a time.
5. Mark a task passed only after verification evidence and audit/review pass.
6. Use a blocker receipt when credentials, accounts, external services, or destructive actions are needed.
7. Do not delete or rewrite tasks to claim completion.
```

The task board is an execution ledger, not the final source of truth. Goal Mode completion still requires the `definition_of_done`, verification, and audit/review to pass.

Recommended files:

```text
.loop-goals/<goal-id>.md
loop-tasks.json
loop-progress.md
blocker-receipt.json
bootstrap.example.sh
```

Safety rules:

- Do not use an unbounded shell loop as the default workflow.
- Do not recommend permission-bypass flags as the normal path.
- Do not treat `passes: true` alone as completion.
- Commit completion only after verification and audit/review pass.
- For UI pages or core interactions, run a browser smoke test and keep screenshot or trace evidence.

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
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_loop_tasks.py examples/coding-project/loop-tasks.json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/housekeep_loop_mode.py --json
```

## License

MIT License. See `LICENSE`.

## Files

- `SKILL.md`：主入口和通用不变量。
- `references/`：长期目标、输出模板、五类场景模板。
- `examples/`：代码项目长跑任务板、进度日志、阻塞 receipt、bootstrap 示例。
- `schemas/`：任务板 JSON Schema。
- `scripts/`：合同校验、长期目标状态校验、任务板校验、自清理脚本。

## Quick Check

```bash
cd loop-mode-generic-skill
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_loop_mode_goal_contract.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_loop_tasks.py examples/coding-project/loop-tasks.json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/housekeep_loop_mode.py --json
```
