---
name: loop-mode-generic
description: 通用 Loop 工作流引擎。把任务拆成可验证的原子操作，按 Intake→Inspect→Route→Execute→Verify→Adversarial Audit→Decide→Report 闭环推进；默认选择最窄入口、复用有效产物、做 targeted verification，并在提交前调用当前运行环境的原生找茬审计子agent复核。触发词："loop"/"Loop模式"/"循环执行"/"用loop" + 任务描述；`/loop mode goal ...` 进入长期目标合同模式。支持自检优化、创作/内容续作、问题修复、长期守护、通用自定义 5 种场景。
author: adam.liu
---

# Loop 模式 — 原子闭环执行引擎

## 心智模型

把目标拆成高确定性的**原子操作**：每个操作输入确定、改动边界单一、验证结果二元、记录可恢复。不是"反复改小错"，也不是"只输出计划"。

## 入口语法

- `/loop mode ...`：普通 Loop 模式，只处理当前任务；除非用户明确要求，不创建长期目标状态文件。
- `/loop mode goal ...` 或 `/loop mode goal: ...`：长期目标模式；`goal` 后必须是空白、冒号或行尾，冒号只是可选分隔符。
- 长期目标模式先把用户的粗略任务整理成 Long Goal Contract，再按原子闭环执行；每轮必须写回 compact 恢复锚点，并在目标未 `complete/blocked/paused` 前持续监控或推进，防止自动压缩后忘记目标、下一步和停机条件。
- 只有输入里没有实际任务、目标存在高风险多义、或需要删除/越权/核心配置授权时才询问；低风险缺项用保守默认补齐并记录。

## 不变量（所有场景继承，唯一权威定义）

**默认行为**
- 目标和成功标准清楚就直接执行；只有关键信息缺失、操作会破坏/删除/越权、或存在多种高风险理解时才停下来问。
- Loop Mode 中禁止无意义请示：长期 goal 下达后，目标范围和停机条件已明确；执行中不得因普通进度确认向用户请示。只有真正目标多义、会破坏/删除数据、或需授权外动作时才问。
- 先读 live 真源（files / DB / logs / checkpoints / APIs）再动手。记忆、摘要、上轮印象只能当索引，不能代替真源。
- 优先复用有效产物、checkpoint、已通过输出和现有证据；禁止为"更干净"重跑已通过/可复用阶段，除非证明上游污染。
- 修流程、配置、提示词、路由、门控，用 targeted acceptance / dry-run / audit-only 证明；普通修复任务不得用正式生产或全链路重跑证明修复。
- 提交任务前必须经过找茬审计：调用**当前运行环境自己的原生子agent**，不得跨工具指定别的 CLI、模型或 agent。审计子agent基于目标、diff、验证证据和剩余风险复核完整性；当前环境没有原生子agent能力时标记 `audit_unavailable`，不得把任务报告为 fully audited。

**原子操作必须四项同时满足**
- 输入确定：依据 live 文件、DB、日志、checkpoint、API 或用户明确文本。
- 影响单一：修一个根因 / 一个合同 / 一个门控 / 一个流程节点 / 一个输出边界。
- 可二元验证：有 pass/fail、diff/readback、dry-run、单测、查询或日志证据。
- 可恢复：有备份、版本控制、checkpoint 或不破坏原始证据。

> 允许一个原子操作触碰多个文件，前提是服务于**同一个合同**（如"代码 + acceptance + 手册同步"）。禁止把多个无关根因塞进同一轮。

## 一轮怎么跑

每轮覆盖 8 个动作；简单任务可内部执行、最终简短汇报，不必机械展开成长报告。

| 步骤 | 必做 | 最小输出 | 禁止 |
|------|------|----------|------|
| 1 Intake | 明确目标/边界/成功标准/授权 | 成功标准·停机条件 | 目标不清还猜测 |
| 2 Inspect | 只读收集现状：文件/日志/DB/进度/进程/手册 | 事实清单 | 未查真源就改 |
| 3 Route | 选最窄有效入口，定义一个原子操作 | 执行卡 | 大范围重构/全链路重跑 |
| 4 Execute | 执行一个原子修改/动作 | 改动范围 | 混合多个无关根因 |
| 5 Verify | 用最便宜且足够的验证证明结果 | 通过/失败证据 | 跳过测试/dry-run/读回 |
| 6 Adversarial Audit | 交给当前运行环境的原生找茬审计子agent复核完整性、证据和风险 | audit pass/fail + findings | 自审冒充外审/忽略审计意见/跨工具换模型 |
| 7 Decide | 验证和审计均通过才收口；失败分类下一轮 | 下一步·停机判断 | 含糊说"应该可以" |
| 8 Report | 汇报改动/验证/审计/风险，必要时落盘 | 最终摘要 | 隐瞒未验证项、审计结论和残留风险 |

**长期目标持续监控不变量**
- `/loop mode goal ...` 的阶段性完成只是 checkpoint，不是交付；只要 `definition_of_done` 未验证通过且未触发阻塞/暂停条件，agent 必须继续监控或推进下一原子动作。
- 启动异步/长耗时任务后，下一步必须写成具体监控动作（进程、日志、产物、DB/checkpoint 或指标），不能写成"已启动，等待完成"后停工。
- 监控必须有有限预算：单次监控窗口、轮询间隔、最大无进展次数、当前 runner 最大监控时长和超时动作都要写明；禁止无限 pull / forever wait / 无界轮询。
- 每次阶段汇报前必须先做 Done Check；未完成时，Report 只能是进度报告，不能作为 final delivery。

**外部找茬审计门**
- 触发点：本轮 Verify 通过后、Decide/Report 之前；长期目标的 `definition_of_done` 最终交付前也必须执行。
- 审计者：必须调用当前运行环境自己的原生子agent，定位是"高细节、强挑刺、零宽容"的审计员；不得在通用 skill 里指定某个 CLI，也不得使用随手可用的其他模型调用顶替。
- 审计输入：用户目标、成功标准、执行卡、关键 diff/产物路径、验证命令与输出摘要、未验证项、剩余风险和 stop conditions。
- 审计任务：找遗漏、未覆盖边界、证据不足、目标偏移、误删/污染风险、过度实现、未同步文档/记忆、未满足用户显式约束。
- 审计证据：优先检查代码/测试/readback/日志/trace/DB/产物等客观证据；模型判断只能补足开放性质量判断，不能替代可运行验证。
- 审计边界：只阻断与成功标准、用户约束、数据安全、质量门控或可恢复性直接相关的实质问题；不得为了风格偏好、目标外优化或无证据怀疑无限找茬。
- 审计预算：首次提交前做全量审计；同一任务审计失败后的复审只看上轮 findings、修复 diff 和受影响验证，除非发现新证据证明范围扩大。
- 审计结论：`pass` 才能进入完成态；`fail` 或 `needs_fix` 必须把 findings 变成下一轮最窄原子动作；审计工具不可用时标记 `audit_unavailable`，不得声称已通过外部审计。

**执行卡**（进入 Execute 前确认；任一项不清且无法低风险确认，回 Inspect 或问一个具体问题）：

```text
用户意图 / 当前真源 / 可复用产物·checkpoint /
最窄入口 / 本轮原子操作 / 误跑·误删·污染成本 /
验证方式 / 是否需要先问用户
```

**验证阶梯**（从最窄开始，只在触及面扩大或 targeted 失败时升级）：
1. 读回/静态检查：确认文件、JSON、schema、prompt、配置真的写入。
2. 单元/合同验收：验证当前原子合同。
3. dry-run/audit-only：验证流程入口和数据边界，不产正式产物。
4. 局部健康检查：验证受影响模块或项目。
5. 全量回归/正式生产：仅在跨边界风险、前面失败、用户明确要求或发布前执行。

## 路由

**精确入口优先于关键词路由。** 输入匹配 `/loop mode goal(\s|:|$)` 时，先进入长期目标合同；其他输入再按意图路由，关键词只是信号不是判据。多场景冲突时按真实意图优先：生产续跑 > 修复 > 诊断 > 问答。若用户在纠正效率/流程安排，进入**纠错锁**：只读核对现状，先修规则或回答原因，不自动 stop / resume / rewrite。

| 意图 | 最窄入口 | 默认验证 | 禁止 |
|------|----------|----------|------|
| 问答/解释 | 只读查证后回答 | 来源/文件行/事实一致性 | 顺手修改或启动流程 |
| 诊断/审计 | 并行只读收集现状 | 问题+证据+优先级 | 未授权直接修高风险项 |
| Bug/流程修复 | 源头修复 + targeted test | 单测/dry-run/readback | 下游贴补丁掩盖根因 |
| 配置/路由/提示词 | 最小合同改动 | smoke/acceptance/audit-only | 用正式生产证明修复 |
| 内容/生产续跑 | 从 latest valid checkpoint | 门控/验收/readback | 重跑已通过/可复用阶段 |
| 长期守护/维护 | 真源 + retention/health gate | health/audit/log/readback | 删高价值或不确定文件 |
| 长期目标/追求目标 | Long Goal Contract + 状态文件 | checkpoint/readback/目标完成判定 | 只靠聊天上下文记目标 |

任务需要更具体模板时，加载对应 reference（模板是执行提示，不覆盖本文件不变量）：

| 触发信号 | 场景 | 模板 |
|----------|------|------|
| 精确前缀 `/loop mode goal(\s|:|$)` | 长期目标合同 | [long-goal.md](references/long-goal.md) |
| 自检/优化/检查系统/10维度/全面检查 | S1 自检优化 | [scene-1-inspect.md](references/scene-1-inspect.md) |
| 写/续写/创作/内容/第X章 | S2 内容续作 | [scene-2-writing.md](references/scene-2-writing.md) |
| 修复/bug/问题/报错/fix | S3 问题修复 | [scene-3-fix.md](references/scene-3-fix.md) |
| 守护/长期/持续/防跑偏/马拉松 | S4 长期守护 | [scene-4-guard.md](references/scene-4-guard.md) |
| 未匹配以上 / 用户自定义 | S5 通用自定义 | [scene-5-generic.md](references/scene-5-generic.md) |

## 终止与升级

- 成功标准全部达成、证据充分 → 收口。
- 当前轮失败但根因清楚、可低风险修复 → 下一轮。
- 需删除/高风险迁移/核心权限变更/目标外生产续跑/付费或账号新增/授权外动作 → 暂停并报告。
- 连续 3 轮同一阻塞点无实质进展（无新增事实、未缩小根因、未改变可验证状态；与耗时无关）→ 停止循环，汇总证据、失败路径和下一步所需输入。

## 自清理

- Skill 真源不得长期保留 `__pycache__`、`.pyc`、`.pyo`、`.DS_Store` 或测试临时缓存。
- 验收/测试默认使用 `PYTHONDONTWRITEBYTECODE=1` 或把 bytecode 输出到 `/tmp`，避免污染真源。
- 低价值生成物可用 `scripts/housekeep_loop_mode.py --apply-generated` 清理；该动作只覆盖缓存/临时文件。
- `_backups` 只做 retention dry-run；删除备份必须显式使用 `--apply-backups --confirm-delete-backups`，且仍受用户删除授权约束。

## 加载更多

- `/loop mode goal ...` 长期目标任务 → 必须加载 [long-goal.md](references/long-goal.md)。
- 需要落盘/输出模板 → [output-formats.md](references/output-formats.md)。

## 跨平台调用

Claude / Codex / CLI：`用 loop 模式执行：目标... 成功标准... 约束... 禁止...`
长期目标：`/loop mode goal 完成...直到[可验证停止条件]`
VS Code / Copilot：`loop: [任务描述]`
不支持持续会话的工具：把本文件作为 system/context 注入；Report 必须落盘，下次从 Inspect 读断点。
