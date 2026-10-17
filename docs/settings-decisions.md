# 本仓设置决策记录

这不是 GitHub 的默认配置，是**逐个字段选过**的。下面每行都能在仓库设置或分支保护里看到，
改任何一项之前先读「理由」和「怎么改回去」。

## 合并方式

| 项 | 取值 | 理由 | 改回去 |
|---|---|---|---|
| squash merge | ✅ 唯一允许 | 一个 PR 压成一个提交，`main` 保持线性；回滚粒度 = 一个 PR | `gh api -X PATCH repos/{o}/{r} -f allow_merge_commit=true` |
| merge commit | ❌ 关闭 | 三种合并路径混用会让历史形状不可预测 | 同上 |
| rebase merge | ❌ 关闭 | 同上 | 同上 |
| squash 提交标题/正文 | `PR_TITLE` / `PR_BODY` | 让 squash 后的提交信息就是 PR 标题 + 正文 | `-f squash_merge_commit_title=COMMIT_OR_PR_TITLE` |
| 合并后删源分支 | ✅ 开 | 单人仓不需要残留分支 | `-f delete_branch_on_merge=false` |
| Update branch 按钮 | ✅ 开 | 分支落后时一键更新，不用本地 rebase | `-f allow_update_branch=false` |

## 分支保护（`main`）

| 项 | 取值 | 理由 |
|---|---|---|
| 必需状态检查 | `checks`（`strict: false`） | 门禁的实体。`strict: false` 不要求分支先变基到最新 `main`——单人仓没必要为顺序付出 rebase 成本 |
| `enforce_admins` | ✅ **true** | **关键项**。为 `false` 时管理员可以绕过必需检查直接推 `main`（实测会在 push 输出里看到 `Bypassed rule violations`）。本仓的目的是「门禁真的拦人」，所以连管理员一起约束 |
| 禁止强制推送 | ✅ | 线性历史 + 禁止改写已发布历史 |
| 禁止删分支 | ✅ | `main` 不该被误删 |
| 线性历史 | ✅ | 与 squash-only 一致，禁止 merge commit 混入 |
| 要求对话解决 | ✅ | 未解决的 review 讨论不能合并 |
| 必须 PR review | ❌ 未启用 | 单人仓，没有第二个 reviewer；开了等于所有 PR 卡死 |

**应急直推怎么办**：先把 `enforce_admins` 或 `allow_force_pushes` 临时改成允许，改完立刻改回来。
两次都必须发**完整 payload**——分支保护是整包替换，漏掉的字段会被置回默认值，而不是保持原样。

## 仓库设置

| 项 | 取值 | 理由 |
|---|---|---|
| Wiki | ❌ 关 | 文档都在这份 README + `references/`，Wiki 是空入口 |
| Projects | ❌ 关 | 只用 issues + PR |
| Issues | ✅ 开 | 缺陷/建议的入口；空白 issue 已关闭，只能走表单 |
| Topics | 10 个 | 可发现性：`github`、`branch-protection`、`rulesets`、`github-actions` 等 |
| License | MIT | 技能内容允许他人复用/改写 |
| 私有漏洞报告 | ✅ 开 | 安全问题的唯一报告入口，见 `SECURITY.md` |

## 故意没有的东西

- **`CODE_OF_CONDUCT.md`**：对外的治理承诺，涉及举报渠道与执行流程，单人仓默认不加；社区健康度因此停在 85%。要加先开 issue 讨论。
- **Dependabot / Renovate**：本仓没有第三方运行时依赖（脚本只用标准库），暂时没有自动升级的对象。
- **Auto-merge 策略**：不在本技能的覆盖范围内（见 `SKILL.md` 的「边界」）。

## 修改这些设置后的固定动作

```bash
python scripts/gh_repo_baseline.py snapshot OWNER/REPO -o now.json          # 改前留档
gh api -X PUT repos/OWNER/REPO/branches/main/protection --input payload.json # 整包写
python scripts/gh_repo_baseline.py check OWNER/REPO --baseline baseline.json # 重新采集复核
```

`check` 退出码 `0` 才算一致；`1` 表示有偏差，逐项确认是「该改仓库」还是「该改基线」。
