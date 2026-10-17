# 社区健康文件

`health_percentage` 由六项组成：README、CONTRIBUTING、LICENSE、CODE_OF_CONDUCT、
issue template、pull request template。健康度只是记账，**真正的判据是这些文件对不对**。

## issue 模板

`.github/ISSUE_TEMPLATE/` 下能放三种东西：`config.yml`（总配置）、`*.yml`（表单）、`*.md`（旧式模板）。
新仓库用 YAML 表单；`*.md` 只在需要「一大段自由文本」时保留。

### config.yml

```yaml
blank_issues_enabled: false
contact_links:
  - name: "📖 使用说明"
    url: https://github.com/OWNER/REPO#readme
    about: 安装、目录结构与快速开始。
```

- `blank_issues_enabled: false` 会隐藏「Blank issue」入口——注意它**对维护者无效**，维护者仍能看到，
  所以别用「网页上还有 Blank issue」证明这项没生效。
- `contact_links` 三项字段 `name` / `url` / `about` 全必填，`url` 必须 `https://`。
- **只放真实可用的链接。** 仓库关着 Discussions 就别放 Discussions 链接；私有漏洞报告没启用
  （`gh api repos/O/R/private-vulnerability-reporting` → `{"enabled": false}`）就别放 `/security/advisories/new`。

### 表单（`*.yml`）

顶层字段：`name`（列表里显示的名字）、`description`、`title`（默认标题前缀）、`labels`、`body`。

`body` 是元素数组，每种元素都有自己的 `type`：

| type | 关键 attributes | validations |
|---|---|---|
| `markdown` | `value`（支持 Markdown） | **不能有**——带上就整份表单校验失败 |
| `input` | `label`、`description`、`placeholder`、`value` | `required` |
| `textarea` | 同 `input`，另可加 `render`（如 `shell` 高亮） | `required` |
| `dropdown` | `label`、`options`（字符串数组）、`multiple` | `required` |
| `checkboxes` | `label`、`options: [{label, required}]` | — |

除 `markdown` 外每个元素都要有全文件唯一的 `id`。

```yaml
name: 🐛 Bug Report / 缺陷反馈
description: 报告可复现的缺陷。
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        提交前请先确认这不是已知问题。
  - type: dropdown
    id: area
    attributes:
      label: 影响范围
      options: ["构建", "文档", "CI", "不确定"]
    validations:
      required: true
```

**YAML 陷阱（会静默截断）**：未加引号的纯量里出现 ` #` 时，YAML 把 `#` 之后当行内注释丢掉——
`name: 🎬 发布流程 (Spec #1)` 会解析成 `🎬 发布流程 (Spec`。
解析成功、行数不变，语法核查完全抓不到。**值里含 ` #` 就加引号**：
`name: "🎬 发布流程 (Spec #1)"`。块标量（`|`）里的 `#` 是字面量，不受影响。

## pull request 模板

`.github/pull_request_template.md`。常见的四段式：变更描述 / 关联 Issue / 变更类型（复选框）/
自查清单。有 CI 的仓库把清单项写成「已运行 `xxx`」这种可核对的句子，而不是「已测试」。

**`Closes #N` 的陷阱**：它出现在 PR 正文的任何位置——包括否定句、反引号里、代码块外——
都会在该 PR 合并时真的关闭 `#N`。想引用而不关闭，写 `Refs #N`。

## CONTRIBUTING.md

写**这个仓库真能跑起来**的东西：真实的目录结构、真实的命令、真实的分支与提交约定。
从别的仓库抄来的 Python 工具链命令在本仓跑不通，比没有这份文件更糟。

结构上够用即可：如何提 issue / 如何改动 / 提交前跑什么 / PR 怎么走。
把核查命令写成能直接复制执行的整行命令，并说明预期输出。

## SECURITY.md

先确认上报渠道**真实可用**，再写进去：

```bash
gh api repos/OWNER/REPO/private-vulnerability-reporting     # {"enabled": true|false}
```

- 启用时：写「通过 GitHub 私有漏洞报告」并给 `/security/advisories/new`。
- 未启用时：给一个真实可达的渠道（例如仓库提交历史里已公开的邮箱），并说明私有报告通道未启用。

**验证陷阱**：维护者本人访问 `/security/advisories/new` 永远能打开「Open a draft security advisory」
草稿页——那是给维护者用的。所以**不能用自己能看到该页面来推断报告人能用**。

响应时限（「48 小时内确认」这类）是替用户做的对外承诺，**写之前问**。

## 要问用户的

`LICENSE` 和 `CODE_OF_CONDUCT.md` 涉及法律与对外治理：许可证要为**每一个**第三方来源核对兼容性，
行为准则要有人真的处理举报。两者都不是「顺手补齐健康度」该做的事——先问，别默认加。
