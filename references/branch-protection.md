# 分支保护

## 端点与整包语义

```bash
gh api repos/OWNER/REPO/branches/BRANCH/protection            # 读（未保护时 404 Branch not protected）
gh api -X PUT repos/OWNER/REPO/branches/BRANCH/protection --input payload.json   # 写
```

`PUT` 是**整包替换**：payload 里没出现的字段会被置回默认值，而不是保持原样。
所以顺序永远是「先读一份完整的 → 改想改的 → 整包写回」。`DELETE` 该端点 = 关闭保护。

**请求是布尔值，响应是对象。** 写 `"allow_force_pushes": false`，读回来是 `{"enabled": false}`。
`enforce_admins` 同理。脚本读 `.enabled`，手写 JSON 时别被这个不对称绊住。

## 字段全表

| 字段 | 含义 | 单人仓常见取值 |
|---|---|---|
| `allow_force_pushes` | 允许强推覆盖历史 | `false` |
| `allow_deletions` | 允许删除该分支 | `false` |
| `enforce_admins` | 管理员也受本规则约束 | `false`（= 管理员仍可绕过） |
| `required_pull_request_reviews` | 合并前必须有人批准 | `null`（单人仓必选，见下） |
| `required_status_checks` | 必须通过的 check | `null` 起步，有 CI 后填 |
| `required_linear_history` | 只接受线性历史 | `false` |
| `required_conversation_resolution` | 未解决的评审对话阻断合并 | `false` |
| `required_signatures` | 要求提交签名 | `false` |
| `lock_branch` | 分支只读（连管理员也不能推） | `false` |
| `allow_fork_syncing` | 允许 fork 同步上游 | `false` |
| `block_creations` | 阻止创建同名分支 | `false` |
| `restrictions` | 谁能推（限用户/团队/应用） | `null` |

一份「禁强推 + 禁删除，其余全默认」的最小 payload：

```json
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false,
  "required_signatures": false
}
```

这正是横幅提示「Protect this branch from force pushing or deletion」对应的那一档，
也是单人维护仓库最常见的选择。

## 单人仓的取舍

- `required_pull_request_reviews` 一旦非 null，就需要「别人」批准；GitHub 不允许自己批准自己的 PR，
  于是维护者会被自己的保护规则锁在门外。单人仓写 `null`。
- `enforce_admins: false` 是刻意的逃生口：规则照常拦普通推送，但管理员仍能强行合并 / 删分支。
  想要「连自己也不能违规」再改成 `true`——改之前确认你确实不需要这个出口。
- `required_status_checks.strict: true` 要求分支合并前必须基于最新 base，代价是每次 base 前进都要
  回来 update branch。单人仓通常 `false`。

## 加上必需状态检查

```json
"required_status_checks": { "strict": false, "contexts": ["checks"] }
```

`contexts` 里写的是 **job 名**（不是 workflow 名）。workflow 叫 `Repository checks`、job 叫 `checks` 时，
GitHub 记录的 context 就是 `checks`——可以用 `gh api repos/O/R/commits/HEAD/check-runs` 或
`gh pr checks N` 核对出来再填，别猜。

**顺序纪律：workflow 必须先落到默认分支，再启用必需状态检查。** 详见 `ci-required-checks.md`。
首次启用要整包 `PUT .../protection`；`PATCH .../protection/required_status_checks` 会返回 404，因为该子资源从未存在过。

## rulesets 还是经典分支保护

| | 经典分支保护 | rulesets |
|---|---|---|
| 免费计划可用范围 | 所有仓库 | **仅 public 仓库**（private 返回 403 `Upgrade to GitHub Pro or make this repository public`） |
| 一个分支被多条规则覆盖 | 只有最宽的那条生效 | 多条叠加，取并集 |
| 读回 | `branches/{b}/protection` | `rulesets` / `rulesets/{id}` |

先查有没有现成的：`gh api repos/O/R/rulesets`。已经是 `[]` 说明这个 owner 走的是经典保护，跟着走即可，
不要为了「更现代」把两套混用——混用时排查「为什么这条能推」会很痛苦。

规则 ID 在网页 `settings/branches` 的 Edit 链接里（`settings/branch_protection_rules/<id>`）。

## 读回复核

```bash
python3 scripts/gh_repo_baseline.py snapshot OWNER/REPO | head -40
```

脚本把请求侧的布尔与响应侧的对象统一成布尔，并显式给出 `protected`、`required_status_checks.contexts`、
`required_pull_request_reviews`（布尔）三个派生量，比直接读原始 JSON 好比对。
