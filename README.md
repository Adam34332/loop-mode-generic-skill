# Loop Mode Generic Skill

通用版 Loop Mode Skill，已剥离私有项目 references，可单独分享给朋友使用。

Signature: adam.liu

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
