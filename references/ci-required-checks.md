# CI 门禁与必需状态检查

必需状态检查只有两种状态：**绿**（放行）和**不是绿**（拦住）。它拦人是靠「有人替你把关」这个假象，
所以最危险的失败模式是 check 根本没跑，而状态显示成中性。

## 最小 workflow 骨架

```yaml
name: Repository checks
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  checks:                     # ← 这个 job 名会成为必需状态检查的 context
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: python3 -m pip install --quiet pyyaml
      # 换成你自己仓的核查脚本
      - run: python3 .github/scripts/check_structure.py
      - name: 随仓一致性核查
        run: |
          if [ -f scripts/consistency-checks.sh ]; then
            bash scripts/consistency-checks.sh
          else
            echo "::notice title=未运行::脚本尚未随仓提供，本步骤记为「未运行」，不代表通过。"
          fi
```

要点：

- `permissions: contents: read` 是最小权限，核查类 workflow 用不到写权限。
- `concurrency` 让同一分支的旧 run 被新 run 取代，省 runner 也省得看陈旧结果。
- `actions/checkout@v5`：`@v4` 依赖 Node 20，runner 会强制改跑 Node 24 并在日志里告警。
- 条件执行的分支要**显式声明「未运行」**——默默跳过会让绿色 check 说谎。

## 启用顺序（顺序搞反就是死锁）

1. 先把 workflow 合进**默认分支**，并确认它在 `push` 事件上真的跑过一次绿的。
2. 再把该 workflow 的 job 名填进 `required_status_checks.contexts`（整包 `PUT .../protection`）。
3. 开一个 PR，观察 `mergeStateStatus` 从 `BLOCKED` 变成 `CLEAN`。

**反过来做会出人命**：如果先启用必需检查、workflow 还没进默认分支，那么所有已经在飞的 PR 的 head
上都产生不了这个 check，它们会被永久判为 BLOCKED。

## 旧 PR 的解死锁

已经存在、head 上还没有该 workflow 的 PR，需要一次新提交才会重跑：

```bash
gh pr update-branch OWNER/REPO#N     # 需要仓库设置 allow_update_branch=true
# 或者往 head 分支推一个空提交
```

关键事实：**推送 base 分支（main）不会重跑 `pull_request` 事件的工作流**。
所以「把 workflow 合进 main」并不足以让旧 PR 变绿，必须动 head。

## 判断 run 到底跑了什么

```bash
gh pr checks N                        # 每个 context 的状态
gh run view <run-id> --log            # 完整日志
gh api "repos/O/R/actions/runs?head_sha=<sha>"   # 按提交查，别靠 gh run list 猜
```

两个坑：

- **日志里出现 `echo "::notice …"` 不等于 else 分支执行了。** GitHub 会把 `run:` 的脚本文本
  回显在 `##[group]Run …` 里。真正的判据是日志中有没有 `##[notice]` 注解行。
- **push 之后 run 不会立刻出现。** 实测有延迟数分钟才创建的情况；此时 `gh run list` 为空不代表
  事件没触发。用 head_sha 查询并等。

## 本地先跑，再让它上 CI

红着推上去，然后对着 Actions 页面调试，是最慢的循环。核查脚本要能在本地一次性跑完：

```bash
python3 .github/scripts/check_structure.py       # 退出码 0/1 必须可信
bash scripts/consistency-checks.sh               # Windows 上用 Git Bash
```

并且**做反向测试**：故意弄坏一处，确认脚本真的退出 1。只验证「正常时是绿的」等于没验证。
