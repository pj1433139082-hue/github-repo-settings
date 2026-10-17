---
name: github-repo-settings
description: GitHub 仓库设置与门禁的配置和审计——分支保护、rulesets、必需状态检查、合并方式、issue/PR 模板、CONTRIBUTING/SECURITY、wiki/discussions 开关；也用于巡视同族仓库取「公共基线」并套到另一个仓、以及证明必需状态检查真的会拦下 PR。Use when setting up or auditing a repository's settings or branch protection, when merges are blocked or the merge button is grey, or when the repo should follow sibling-repo conventions.
---

# GitHub 仓库设置与门禁

设置这件事有两种失败模式：**改错了没人发现**，和**以为改了其实没生效**。
下面六步让这两种都留下证据；跑完之前不声称完成。

前提：`gh` 已登录（`gh auth status` 通过），且账号对目标仓有 admin 权限。
脚本在技能根目录的 `scripts/` 下，只用标准库 + `gh`（macOS/Linux 用 `python3`，Windows 用 `python`）。
示例里的 `-o` 一律写相对文件名：PowerShell 没有 `/tmp`，要临时目录就写 `$env:TEMP\now.json`。

## 先分类

| 用户要的 | 走 |
|---|---|
| 「给这个仓配上保护 / issue 模板 / PR 设置」 | 全流程 1 → 6 |
| 「别的仓是怎么设的？有没有公共设置？」 | 1 → 2，然后停下来报告 |
| 「审计一下这个仓的设置对不对」 | 1 → 2 → 4 → 6 |
| 「PR 卡住了 / merge 按钮是灰的 / BLOCKED」 | 直接读 `references/ci-required-checks.md` |

## 步骤

### 1. 读现状，不凭印象

```bash
python3 scripts/gh_repo_baseline.py snapshot OWNER/REPO -o now.json
```

一次采全：仓库设置、默认分支保护、rulesets、工作流清单、社区健康度。
`protected: false` 是常态——GitHub 不会替你保护任何分支。

### 2. 取基线

把「公共设置」先当**事实**测出来，再当**建议**用：

```bash
python3 scripts/gh_repo_baseline.py survey OWNER --limit 30 -o baseline.json
```

输出两段：`common`（所有被巡视仓库取值一致的项）与 `distribution`（取值分布）。
`common` 是事实不是建议——`license`、`wiki`、`topics` 这类本就该因仓而异的项，
即使 13/15 一致也要单独判断。判定规则见 `references/baseline-survey.md`。

### 3. 应用

用 `gh api -X PUT/PATCH` 写，payload 走文件（避免 PowerShell 引号地狱）：

```bash
gh api -X PUT repos/OWNER/REPO/branches/BRANCH/protection --input protection.json
gh api -X PATCH repos/OWNER/REPO --input repo-settings.json
```

保护配置是**整包替换**：payload 里漏掉的字段会被置回默认值，而不是保持原样。
所以先读完现状，再把完整 payload 写出去。字段全表与单人仓取舍见 `references/branch-protection.md`。

### 4. 读回复核

```bash
python3 scripts/gh_repo_baseline.py check OWNER/REPO --baseline baseline.json
```

退出码 `0` = 与基线一致，`1` = 有偏差并逐项列出，`2` = 用法或基线文件问题。
`check` 是**重新采集**而不是回显刚写的东西——这正是它能抓到「写失败」的原因。

### 5. 让门禁真的拦一次

必需状态检查只在 check 处于 pending 时拦人。开一个 PR，在 check 还没跑完时看
`mergeStateStatus`：应当是 `BLOCKED`；check 转绿后变 `CLEAN`。
**没观察到这次转变，就不要声称门禁有效。**

### 6. 报告

把「已核实」与「未核实」分开写，每条附上产生它的命令或日志行。
未运行的项目就写「未运行」——不写「通过」。

## 四条硬纪律

1. **workflow 先落到默认分支，再启用必需状态检查。** 反过来会让所有在飞的 PR 永远等一个产生不出来的 check。
2. **从未启用过的子资源不能 PATCH。** 例：首次开启必需状态检查时 `PATCH .../required_status_checks` 返回 404，改用整包 `PUT .../protection`。
3. **要引用而不关闭工单，写 `Refs #N`。** `Closes #N` 出现在正文任何位置——包括否定句和反引号里——都会在合并时真的关掉它。
4. **一次只动一个面，然后读回。** 设置/保护/模板/CI 分次落，每次都有独立的读回证据。

## 参考

| 文件 | 什么时候读 |
|---|---|
| `references/baseline-survey.md` | 选巡视对象、判定哪些项该随大流、基线文件格式 |
| `references/branch-protection.md` | 保护字段全表、整包 payload、单人仓取舍、rulesets 与经典保护 |
| `references/community-health.md` | issue 表单 / PR 模板 / CONTRIBUTING / SECURITY / CODE_OF_CONDUCT |
| `references/ci-required-checks.md` | workflow 骨架、check 名字从哪来、启用顺序、解死锁 |
| `references/verification.md` | 三重验证法：API 读回 / 浏览器实测 / CI 日志取证 |
| `references/pitfalls.md` | 踩过的坑：现象 → 根因 → 做法 |

## 边界

本技能只写**在真实仓库上跑通过**的那一层：仓库设置、分支保护、必需状态检查、社区健康文件、CI 门禁顺序。

没有覆盖：auto-merge 策略、reusable workflow 的编写与消费、Dependabot / Renovate 配置、AI reviewer 的拉锯、组织级安全设置、harden-runner。
这些都需要时另找上游 —— `netresearch/github-project-skill` 是同类里覆盖最全的一份（`skills/github-project/` 下有 28 篇 references，外加 `init-branch-protection.sh` 与 `checkpoints.yaml`），代价是体量大、要读的东西多。
本技能是独立撰写的中文轻量版，未复制其文本；结构灵感来自上面这份。

