# github-repo-settings

> GitHub 仓库设置与门禁的配置和审计：分支保护、rulesets、必需状态检查、合并方式、issue / PR 模板、社区健康文件，以及「证明门禁真的会拦人」。

一个纯文本 Agent Skill——`SKILL.md`（给智能体读的流程）+ 6 篇 `references/`（字段全表与踩坑）+ 1 个只读 Python 脚本。
**不收集凭据、不自己发写请求**：所有写入仍由人或 agent 显式执行 `gh api -X PUT/PATCH`，脚本只做「采集 / 基线 / 校验」。

![checks](https://github.com/pj1433139082-hue/github-repo-settings/actions/workflows/checks.yml/badge.svg)

适用于遵循 `SKILL.md` 约定（frontmatter 里写 `name` 与 `description`）的智能体，例如 Claude Code 及其兼容实现。

## 它解决什么

设置仓库这件事有两类失败：**改错了没人发现**，和**以为改了其实没生效**。
`SKILL.md` 用六步让这两种都留下证据：

| 步骤 | 做什么 | 留下什么证据 |
|---|---|---|
| 1 | `snapshot` 读现状 | JSON 快照 |
| 2 | `survey` 巡视同族仓库，测出「公共基线」 | `common` / `distribution` 两段输出 |
| 3 | `gh api -X PUT/PATCH` 应用（payload 走文件） | 实际请求命令 |
| 4 | `check` **重新采集**后与基线比对 | 退出码 0/1 + 逐项偏差 |
| 5 | 开 PR 观察 `mergeStateStatus`：`BLOCKED` → `CLEAN` | PR 状态转变 |
| 6 | 报告分「已核实 / 未核实」两栏 | 每条附命令或日志行 |

第 4 步是这套东西的价值所在：`check` 是重新请求一次，而不是回显你刚写出去的 payload——所以它能抓到「写失败」和「有人又在 UI 上改回去了」。

## 它不做什么

auto-merge 策略、reusable workflow 的编写与消费、Dependabot / Renovate 配置、AI reviewer 的拉锯、组织级安全设置、harden-runner。
这些需要时看文末「上游」。

## 前置条件

- `gh` CLI 已登录（`gh auth status` 通过）
- 对目标仓库有 **admin** 权限（分支保护与仓库设置都要求 admin）
- Python 3（只 import 标准库，无第三方依赖）

## 安装

把本目录整个放到技能目录下，二选一：

```bash
# 项目级：只在这个仓库里可用
git clone https://github.com/pj1433139082-hue/github-repo-settings .claude/skills/github-repo-settings

# 用户级：所有项目可用（旧路径 ~/.claude/skills 同样生效）
git clone https://github.com/pj1433139082-hue/github-repo-settings ~/.agents/skills/github-repo-settings
```

不放 git 也行，直接复制目录亦可。装好后检查：**目录名必须叫 `github-repo-settings`，且与 `SKILL.md` frontmatter 的 `name` 一致**，否则技能不会被发现。

## 快速开始

在技能根目录下执行（示例用 `python3`，Windows 用 `python`）：

```bash
# 1. 读现状（只读）
python3 scripts/gh_repo_baseline.py snapshot OWNER/REPO -o now.json

# 2. 取基线（只读）
python3 scripts/gh_repo_baseline.py survey OWNER --limit 30 -o baseline.json

# 4. 读回复核（只读）—— 0=一致，1=有偏差，2=用法或基线文件问题
python3 scripts/gh_repo_baseline.py check OWNER/REPO --baseline baseline.json
```

`snapshot` 的真实输出（在公开仓上实跑，截取字段）：

```json
{
  "repo": "netresearch/github-project-skill",
  "default_branch": "main",
  "protection": { "protected": false },
  "workflows": ["auto-merge-deps.yml", "lint.yml", "scorecard.yml", "tests.yml"]
}
```

`protected: false` 是常态——GitHub 不会替你保护任何分支。
`check` 失败时逐项打印 `✗ key: 实际 ≠ 基线`，也可以用 `--json` 拿机器可读结果。

## 四条硬纪律（摘自 SKILL.md）

1. **workflow 先落到默认分支，再启用必需状态检查。** 反过来会让所有在飞的 PR 永远等一个产生不出来的 check。
2. **从未启用过的子资源不能 PATCH。** 首次开启必需状态检查时 `PATCH .../required_status_checks` 返回 404，改用整包 `PUT .../protection`。
3. **保护配置是整包替换。** payload 里漏掉的字段会被置回默认值，所以顺序永远是「先读完整现状 → 改想改的 → 整包写回」。
4. **要引用而不关闭工单，写 `Refs #N`。** `Closes #N` 出现在正文任何位置——包括否定句和反引号里——都会在合并时真的关掉它。

## 跨平台

- `python3` ↔ `python`：macOS/Linux 用前者，Windows 用后者。
- `-o` 一律写相对文件名。PowerShell 没有 `/tmp`，要临时目录就写 `$env:TEMP\now.json`。
- PowerShell 下 `gh api --input` 的 JSON **走文件**，别把 payload 拼到命令行（引号会打架）。
- PowerShell 变量名大小写不敏感：`$R` 与 `$r` 是同一个变量，别靠大小写区分。
- 分支保护列表的网页入口是 `settings/branches`；`settings/branch_protection_rules` 会 404。

## 目录结构

```
SKILL.md                    主流程：分类 → 六步 → 四纪律 → 边界
references/
  baseline-survey.md        巡视对象怎么选、common 是事实不是建议、基线文件格式
  branch-protection.md      保护字段全表、最小 payload、单人仓取舍、rulesets vs 经典保护
  community-health.md       issue 表单 / PR 模板 / CONTRIBUTING / SECURITY / CODE_OF_CONDUCT
  ci-required-checks.md     workflow 骨架、context 名字从哪来、启用顺序、解死锁
  verification.md           三重验证：API 读回 / 浏览器实测 / 行为证据
  pitfalls.md               14 条踩坑：现象 → 根因 → 做法
scripts/
  gh_repo_baseline.py       snapshot / survey / check 三件套（只读，凭据交给 gh）
```

## 已知限制

- **private 仓在免费计划下用不了 rulesets**（`403 Upgrade to GitHub Pro or make this repository public`），只能用经典分支保护。
- **单人仓不能开「必须有人批准」**：GitHub 不允许自己批准自己的 PR，开了就把维护者锁在门外，`required_pull_request_reviews` 保持 `null`。
- `community/profile` 的 `files.issue_template` 对 YAML 表单的检测口径与网页不一致——以线上 `issues/new/choose` 为准，API 字段只用来判断「有没有」。
- `@actions/checkout@v4` 在 runner 上会被强制改跑 Node 24 并告警，建议 `@v5`。
- 文里的版本事实（404 行为、context 命名、run 延迟数分钟才创建）都是某一时刻的实测，换 GitHub 版本需重新核对。

## 实测范围（诚实栏）

- 已实测：Windows 10.0.26100 / PowerShell 7.6.7 / `gh` 2.89.0 / Python 3.13.9；`--help` 正常，`snapshot` / `survey` 在公开仓实跑通过（exit 0），`check --baseline` 读回一致（exit 0），`check` 缺基线返回 2。
- 实测中的一个真实边界：`survey` 遇到个别仓库 API 连接中断（`EOF`）时整轮返回 1、且不写出基线文件——这是有意的「宁缺勿假」，换个网络重跑即可。
- 未实测：macOS / Linux 下的 shell 片段（脚本本身只用标准库与 `gh`，差异集中在 shell 语法）；组织级设置；企业版。

## 来源与致谢

- 正文为独立撰写（中文），**未复制**任何上游文本。
- 结构灵感来自 [`netresearch/github-project-skill`](https://github.com/netresearch/github-project-skill)：其 `skills/github-project/` 下有 28 篇 references，另有 `init-branch-protection.sh` 与 `checkpoints.yaml`，覆盖比本技能广（含 auto-merge、reusable workflow、org security），代价是体量大、要读的东西多。该仓库在 GitHub 上显示的许可证为 `NOASSERTION`（识别不出标准协议），因此这里刻意重写而非搬运。
- 六步、三重验证、四条硬纪律与 `pitfalls.md` 的 14 条，都来自在真实仓库上的实操：先踩坑，再写成规则。

## License

MIT，见 [LICENSE](LICENSE)。
