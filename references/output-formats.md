# 落盘与输出模板

按需取用；模板是提示不是硬约束，字段按场景增删。所有场景的落盘共用同一骨架：**做了什么 → 验证结果 → 剩余风险**。

## 通用 Loop 记录

```markdown
## Loop 记录 — [日期]
- 目标 / 成功标准：
- 第 N 轮：[原子操作] → 验证 pass/fail
- 结论：完成 / 下一轮 / 暂停等授权
- 剩余风险：
```

## Long Goal Contract / compact 恢复锚点

用于 `/loop mode goal ...`。状态文件必须能让任意后续工具在 auto-compact 后只凭文件恢复目标。

````markdown
# Long Goal Contract: [goal_id]

status: active
created_at: [ISO time]
updated_at: [ISO time]
owner_tool: [codex/claude/vscode/etc]
state_path: [absolute path]
state_path_aliases: [optional absolute paths for other hosts, or none]
lock_path: [state_path + ".lock"]
lock_path_aliases: [optional absolute lock paths for other hosts, or none]
goal_revision: 1

## Goal Snapshot
- 原始请求：[用户原文]
- 最终目标：[一句话]
- 完成判定：[可验证结果]
- 当前阶段：[phase/checkpoint]
- 当前 checkpoint：[已完成且验证通过的边界]
- 下一步：[一个原子动作]
- 进度监控：[目标未完成前下一次查什么]
- 停止条件：[成功/阻塞/授权/风险]

## Scope
- 必做：
- 不做：
- 允许改动：
- 禁止改动：
- 目标内授权：[目标范围内可自动执行的动作]
- 仍需授权：[删除/不可逆/付费/新增账号/目标外生产/降低质量门控等]

## Authority Sources
- 必读真源：
- 可复用产物/checkpoint：
- 不能当真源的内容：

## Execution Loop
- 每轮最多原子动作数：1-3
- 本轮原子动作：
- 验证方式：
- 进度探针：[进程/日志/产物/DB/checkpoint/API/指标]
- 外部找茬审计：[current-runtime-native-subagent；审计输入/实质问题阻断规则]
- 写回要求：每轮更新 Goal Snapshot、Progress Log、Progress Monitor、Adversarial Audit Gate、Compact Resume Anchor
- 健康检查：每轮先验证必填字段、resume anchor、lock、next_action

## Adversarial Audit Gate
- auditor: [current-runtime-native-subagent or audit_unavailable]
- audit_trigger: [after Verify, before Decide/Report; final done check required]
- audit_inputs: [goal/success criteria/diff/artifacts/verification evidence/risks]
- audit_scope: [completeness/evidence gaps/user constraints/data safety/quality gates/recoverability]
- pass_condition: [no material finding tied to success criteria or explicit constraints]
- fail_action: [convert findings into next narrow atomic action]
- unavailable_action: [do not mark complete; keep active or blocked with evidence]
- last_audit_status: [pending/pass/fail/needs_fix/audit_unavailable]

## Runner Lock
- lock_path: [absolute path]
- lock_path_aliases: [optional absolute lock paths for other hosts, or none]
- active_runner: [tool/session/pid if available]
- acquired_at: [ISO time]
- heartbeat: [ISO time]
- stale_after: [duration, default 30m unless task needs longer]

## Progress Monitor
- phase_complete_is_not_done: true
- monitor_backend: [claude-code-monitor/codex-exec-session/tmux/launchd-cron/state-file-poll/manual-poll]
- monitor_task_id: [Monitor task id, tmux session, pid, job id, or none]
- monitor_target: [PID/session/log/event-log/DB/checkpoint/report/API]
- monitor_event_sink: [output file/log/API/dashboard URL/state file]
- monitor_window: [single active observation window, e.g. 10m/30m/2h]
- monitor_cadence: [event-driven, after each command, or interval-based]
- monitor_interval: [finite poll interval, e.g. 30s/2m/5m, or after each event]
- monitor_max_no_progress: [positive integer]
- monitor_max_runtime: [finite runner lease, e.g. 30m/2h/6h]
- monitor_on_timeout: [writeback + handoff / mark blocked / pause with evidence]
- monitor_next_probe: [one concrete next check]
- monitor_stop_when: [definition_of_done verified or stop condition triggered]
- monitor_escalate_when: [no progress for N probes / error pattern / stale lock / service down]
- monitor_fallback: [state-file-poll/log-tail/manual-poll path if backend unavailable]

## Progress Log
| 时间 | 轮次 | 动作 | 验证 | 结论 | 下一步 |
|------|------|------|------|------|--------|

## Compact Resume Anchor
```text
LONG_GOAL_RESUME
state_path: [absolute path]
state_path_aliases: [optional absolute paths for other hosts, or none]
lock_path: [absolute path]
lock_path_aliases: [optional absolute lock paths for other hosts, or none]
goal_id: [goal_id]
status: active
goal_snapshot: [目标/完成判定/当前checkpoint的8行内摘要]
current_checkpoint: [verified boundary]
next_action: [one atomic action]
monitor_next_probe: [one concrete progress check]
verification_required: [command/readback/test/report]
adversarial_audit_required: true
adversarial_audit_status: [pending/pass/fail/needs_fix/audit_unavailable]
stop_if: [done/block/delete/core-config/target-out-of-scope/paid-or-account-change/active-lock/state-invalid/3x-same-blocker/user-pause]
```
````

## S1 自检优化

```markdown
## 自检报告 — [日期]
### 维度扫描
| 维度 | 状态 | 问题数 | 详情 |
|------|------|--------|------|
| D1 | green/yellow/red | n | ... |
### 修复记录
| # | 问题 | 根因 | 修复 | 验证 |
|---|------|------|------|------|
| 1 | ... | ... | ... | pass/fail |
### 剩余风险
- [未关闭项]
```

## S2 内容续作

```markdown
## 内容进度 — [日期]
- 项目 / 已完成范围 / 当前阶段 / 精确断点：
### 本轮记录
| 单元 | 阶段 | 状态 | 质量 | 备注 |
|------|------|------|------|------|
| X | ... | pass/fail/warn | ... | ... |
### 偏差记录
- [现象 / 原因 / 纠正]
### 下一步
- 待读文件 / 注意事项：
```

## S3 问题修复

```markdown
## 修复记录 — [日期]
- 现象 / 根因 / 影响范围：
- 文件 + 改动（最小改动·根因修复）：
- 验证：[测试/dry-run/读回] → pass
- 风险：[副作用 / 是否需后续观察]
```

## S4 长期守护

```markdown
## 守护记录 — [日期]
- 目标 / 当前 checkpoint / 下次监控：
- 本轮事实：
- 本轮动作：
- 验证：
- 下一步：
- 停机条件是否触发：
```
