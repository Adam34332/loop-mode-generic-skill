# 长期目标合同

适用信号：精确入口 `/loop mode goal(\s|:|$)`。`goal` 后直接接任务要求，冒号可选；`goal` 后不是空白、冒号或行尾时不触发长期目标。

本模板用于模拟 Goal 的关键效果：一个可恢复的目标、明确的完成判定、每轮 checkpoint、compact 后可继续的状态锚点。它不是后台 daemon；会话结束、权限缺失、删除/越权动作、连续阻塞等仍按主文件停机规则处理。

通用八步闭环、执行卡、验证阶梯和外部找茬审计门见 SKILL.md。长期目标的状态落盘见 [output-formats.md](output-formats.md) 的 Long Goal 模板。

## 目标

- 防止 auto-compact 或跨工具接力后忘记目标、边界、下一步和停止条件。
- 把用户的粗略任务自动整理成 Long Goal Contract。
- 每轮只推进 1-3 个原子动作，验证后写回状态文件。
- 目标未完整完成前，阶段性完成只算 checkpoint；必须继续监控或推进下一步。
- 达到成功标准后自动停止，不继续寻找额外工作。

## 入口分流

| 输入 | 行为 |
|------|------|
| `/loop mode ...` | 普通 Loop 模式，不创建长期目标合同 |
| `/loop mode goal ...` | 创建/读取 Long Goal Contract 并按目标推进 |
| `/loop mode goal: ...` | 同上，冒号仅作可选分隔符 |
| `/loop mode goal` 后无任务 | 问一个问题：长期目标是什么？ |
| `/loop mode goalpost ...` 等 | 不匹配 goal 入口，走普通 Loop 路由 |

如果用户误把一次性任务写成 goal，也仍可创建合同，但 `每轮执行预算=1`、`成功后立即 complete`，避免无意义长跑。

## Intake 自动整理规则

从用户原文提取并补齐：

1. `final_objective`：最终要完成什么。
2. `definition_of_done`：什么证据证明已完成。
3. `scope` / `non_goals`：做什么、不做什么。
4. `authority_sources`：每轮必须先读的真源、手册、DB、日志或状态文件。
5. `state_path`：长期目标状态文件。
6. `verification_loop`：每轮如何验证进展。
7. `adversarial_audit_gate`：提交前由当前运行环境的原生找茬审计子agent复核、审什么、失败后怎么回到下一轮。
8. `stop_conditions`：成功、阻塞、授权、风险、预算等停机条件。
9. `next_action`：下一步唯一原子动作。
10. `progress_monitor`：目标未完成前下一次检查什么进程、日志、产物、DB/checkpoint、API 或指标。
11. `monitor_budget`：单次监控窗口、轮询间隔、最大无进展次数、当前 runner 最大监控时长和超时动作。

缺少低风险细节时用保守默认，并在合同中标记 `assumption`。缺少会导致误删、越权、核心配置改动、目标外生产恢复、付费/账号新增或边界不明的信息时先问。

## 状态文件默认位置

优先使用最靠近任务真源的位置：

1. 任务明确属于某个项目/仓库：`<project_or_repo>/.loop-goals/<goal_id>.md`。
2. 跨工具或共享任务：`<shared_workspace>/loop-goals/<goal_id>.md`。
3. 路径不明确且写错会污染项目时，先问用户确认。

`goal_id` 用 `YYYYMMDD-HHMM-<short-slug>`，只含小写字母、数字和连字符。

## 必填合同字段

````markdown
# Long Goal Contract: <goal_id>

status: active | blocked | complete | paused
created_at:
updated_at:
owner_tool:
state_path:
state_path_aliases:
lock_path:
lock_path_aliases:
goal_revision:

## Goal Snapshot
- 原始请求：
- 最终目标：
- 完成判定：
- 当前阶段：
- 当前 checkpoint：
- 下一步：
- 进度监控：
- 停止条件：

## Scope
- 必做：
- 不做：
- 允许改动：
- 禁止改动：
- 目标内授权：
- 仍需授权：

## Authority Sources
- 必读真源：
- 可复用产物/checkpoint：
- 不能当真源的内容：

## Execution Loop
- 每轮最多原子动作数：
- 本轮原子动作：
- 验证方式：
- 外部找茬审计：
- 进度探针：
- 写回要求：

## Adversarial Audit Gate
- auditor:
- audit_trigger:
- audit_inputs:
- audit_scope:
- pass_condition:
- fail_action:
- unavailable_action:
- last_audit_status:

## Runner Lock
- lock_path:
- lock_path_aliases:
- active_runner:
- acquired_at:
- heartbeat:
- stale_after:

## Progress Monitor
- phase_complete_is_not_done:
- monitor_backend:
- monitor_task_id:
- monitor_target:
- monitor_event_sink:
- monitor_window:
- monitor_cadence:
- monitor_interval:
- monitor_max_no_progress:
- monitor_max_runtime:
- monitor_on_timeout:
- monitor_next_probe:
- monitor_stop_when:
- monitor_escalate_when:
- monitor_fallback:

## Progress Log
| 时间 | 轮次 | 动作 | 验证 | 结论 | 下一步 |
|------|------|------|------|------|--------|

## Compact Resume Anchor
```text
LONG_GOAL_RESUME
state_path:
state_path_aliases:
lock_path:
lock_path_aliases:
goal_id:
status:
goal_snapshot:
current_checkpoint:
next_action:
monitor_next_probe:
verification_required:
adversarial_audit_required:
adversarial_audit_status:
stop_if:
```
````

## 每轮执行协议

1. **Resume**：先读 `state_path`。如果文件不存在，先创建合同；如果存在，按 `Compact Resume Anchor` 恢复，不靠聊天上下文。
2. **Validate**：运行状态文件健康检查；缺必填字段、锚点不一致或 `next_action` 含糊时，先修状态文件或暂停。
3. **Lock**：写入/刷新 `lock_path`。发现其他活跃 runner 且未过期时停止，避免双写；过期锁只允许在记录证据后接管。
4. **Done Check**：执行前先验证 `definition_of_done`。已满足则写 `status: complete` 并停止。
5. **Inspect**：只读收集本轮 `next_action` 所需真源。
6. **Execute**：执行 1-3 个同一目标下的原子动作；写操作串行。
7. **Verify**：运行合同中的最小验证；失败必须分类根因。
8. **Adversarial Audit**：Verify 通过后，把目标、diff/产物、验证证据、剩余风险交给当前运行环境的原生找茬审计子agent；不得跨工具指定别的 CLI、模型或 agent。审计 `pass` 才能继续交付，`fail/needs_fix` 必须回到下一轮最窄修复，当前环境没有原生子agent能力时标记 `audit_unavailable`，默认不能置为 complete。
9. **Progress Probe**：目标未完成时，检查 `progress_monitor` 指定的进程、日志、产物、DB/checkpoint、API 或指标，确认是否继续、重试、接管或升级。
10. **Writeback**：更新 `Progress Log`、`Goal Snapshot`、`Progress Monitor`、`Adversarial Audit Gate`、`Compact Resume Anchor`，并刷新 lock heartbeat。
11. **Decide**：`definition_of_done` 和外部找茬审计都通过才交付；未完成则继续监控/推进下一原子动作；触发停机条件则 `blocked/paused` 并报告。

## 持续监控协议

- `phase_complete_is_not_done` 必须写明：阶段完成、批次启动、脚本通过、进程启动等都不是最终交付，除非同时满足 `definition_of_done`。
- `monitor_backend` 必须写明承载机制：`codex-exec-session`、`claude-code-monitor`、`tmux`、`launchd/cron`、`state-file-poll`、`manual-poll` 等；不可用时必须写 fallback。
- `monitor_target` 必须是可查对象：PID/session、日志路径、event-log、DB/checkpoint、测试报告、外部队列或明确 URL/API。
- `monitor_next_probe` 必须是下一次能执行的具体检查，不能写成"继续观察"、"等待完成"。
- `monitor_window` 是单次主动监控窗口，`monitor_max_runtime` 是当前 runner/后台监控租约上限；两者必须是有限时长，禁止 `infinite`、`forever`、`无限`、`一直等`。
- `monitor_interval` 必须是有限轮询间隔，或精确写成 `after each event` / `after each command` / `event-driven` / `command-driven`；禁止紧密 busy loop，也禁止无限 sleep。
- `monitor_max_no_progress` 必须是正整数；达到后按 `monitor_on_timeout` 写回状态、交接、升级或暂停。
- `monitor_on_timeout` 必须说明超时后的动作：写回 `Progress Log`/`Compact Resume Anchor`、刷新或释放 lock、标记 `active` 交接下一窗口，或在有明确故障时置为 `blocked/paused`。
- 长耗时任务可短暂等待或周期性轮询；每次轮询都要有证据增量，发现无增量按阻塞计数处理。
- agent 不能在 `status: active` 且 `definition_of_done` 未满足时把阶段性 Report 当最终回答；只能报告进度，并继续同一 goal loop。
- 如果工具/会话限制导致无法继续监控，必须先写回 `active` 状态、明确 `monitor_next_probe` 和恢复锚点，再说明尚未交付。

## 并发与锁

- `lock_path` 默认是 `state_path + ".lock"`，内容写明 runner、pid/session、开始时间、heartbeat、当前原子动作。
- 跨机器时必须写 `lock_path_aliases`；实际写锁使用与当前 `state_path` / `state_path_aliases` 同平台的 lock 路径。
- 同一 `state_path` 同时只能有一个 active runner。另一个工具看到未过期 lock 时，只能读状态和报告，不能继续写。
- stale lock 判定必须有证据：本机 PID 不存在、远端会话明确结束，或 `heartbeat` 超过 `stale_after` 且无活跃进程/日志增长。
- 接管 stale lock 前，在 `Progress Log` 记录接管原因；不确定时暂停而不是双写。

## auto-compact 防丢规则

- 每轮结束必须把 `Goal Snapshot` 控制在 8 行以内，确保 compact 摘要能抓住核心。
- 最后一段报告必须包含 `LONG_GOAL_RESUME` 块或说明状态文件路径。
- compact 后第一动作永远是读 `state_path`，不得凭摘要继续。
- `next_action` 必须是一个可执行原子动作，不能写成"继续推进"。
- `monitor_next_probe` 必须是具体监控动作，不能写成"等待完成"。
- `monitor_window` / `monitor_max_runtime` 必须是有限时间；compact 摘要不能把监控写成无限等待。
- `stop_if` 必须包含成功停止条件和需要用户授权的停止条件。
- `adversarial_audit_required` 和 `adversarial_audit_status` 必须写进恢复锚点；compact 后不得把未审计状态当完成。

## 应急恢复

按顺序处理，不跳级：

1. `state_path` 不存在：从用户原始 goal 或最近一条 `LONG_GOAL_RESUME` 重建合同；没有足够信息就问。
2. 状态文件可读但锚点缺失：先从 `Goal Snapshot` 和 `Progress Log` 重建 `Compact Resume Anchor`，不执行任务。
3. legacy active 状态缺 `Progress Monitor`、`monitor_backend`、`monitor_budget` 或 `monitor_next_probe`：先从日志、状态文件、checkpoint 或产物补具体监控字段和有限预算；验证状态文件后再继续任务；不得因缺字段直接把 active goal 当完成或放弃。
4. `Goal Snapshot` 与 `Compact Resume Anchor` 冲突：以最新通过验证的 `Progress Log` 为准；无法判断则 `status: blocked`。
5. 当前平台路径与 `state_path` 不一致：检查 `state_path_aliases`；命中别名则继续，并使用同平台 `lock_path_aliases`；未命中则暂停并补别名，不猜路径。
6. `next_action` 含糊或不可验证：只做 Inspect，重写为一个原子动作后停止或等待下一轮。
7. 写回失败：停止执行，报告 state/lock 路径和最后成功 checkpoint；不得继续靠聊天上下文推进。
8. 发现目标已漂移：增加 `goal_revision`，保留旧目标摘要；新目标必须有新的完成判定和停机条件。

## 自动停止条件

满足任一条件必须停止：

- `definition_of_done` 的验证全部通过。
- 当前任务被证据证明不需要长期目标，且一次性目标已经完成。
- 连续 3 轮同一阻塞点无新增事实、未缩小根因、未改变可验证状态。
- 下一步需要删除文件、核心配置/agent/权限变更、目标外生产恢复、付费/新增账号/外部高风险动作，且用户未明确授权。
- 状态文件不可读/不可写，导致 compact 后无法恢复。
- 未过期 runner lock 存在，或状态文件健康检查失败且无法自动修复。
- 用户要求暂停、清空、改目标，或新请求与当前目标冲突。

## Prompt 模板

```markdown
/loop mode goal 完成 [目标]，直到 [可验证停止条件]。
约束：[必须遵守]
禁止：[绝对不能做]
真源：[必须先读的文件/DB/日志]
验证：[证明完成的命令/报告/状态]
```
