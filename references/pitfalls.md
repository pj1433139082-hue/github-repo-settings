# 踩过的坑

每条都是**现象 → 根因 → 做法**。现象栏照原样留着，好让人能搜到自己的报错。

## 1. YAML 值里的 ` #` 被静默吃掉

- 现象：网页上 contact link 显示成 `🎬 发布流程 (Spec`，末尾没了。
- 根因：未加引号的纯量中 ` #` 起行内注释。解析成功、行数不变、只是值变短。
- 做法：值里含 ` #` 就加引号，例如 `name: "🎬 发布流程 (Spec #1)"`。块标量 `|` 内不受影响。

## 2. `PATCH .../required_status_checks` 返回 404

- 现象：首次开启必需状态检查时报 `gh: Required status checks not enabled (HTTP 404)`。
- 根因：从未启用过的子资源不存在，不能局部 PATCH。
- 做法：改用整包 `PUT .../branches/BRANCH/protection`，payload 带齐全部字段。

## 3. `Closes #N` 在否定句里也生效

- 现象：PR 正文写「因此不 `Closes #11`」，合并后 issue #11 真的被关闭。
- 根因：GitHub 的关联关键字解析器不读语义，反引号与否定词都不构成豁免。
- 做法：只想引用时写 `Refs #N`。合并后回头核对被自动关闭的工单。

## 4. `gh` 按当前目录推断仓库

- 现象：`failed to get run: HTTP 404: Not Found (https://api.github.com/repos/OWNER/<另一个仓>/actions/runs/…)`。
- 根因：在 clone 目录外执行 `gh run view`，gh 用 cwd 猜仓库。
- 做法：跨目录时一律带 `-R OWNER/REPO`。

## 5. PowerShell 变量名大小写不敏感

- 现象：`expected the "[HOST/]OWNER/REPO" format, got "run=… status=completed"`。
- 根因：`$R` 与 `$r` 是同一个变量，赋给 `$r` 把 `$R` 覆盖了。
- 做法：脚本里用区分度高的名字（`$repo`、`$runId`），不要靠大小写区分。

## 6. .NET 静态方法按进程启动目录解析相对路径

- 现象：`Could not find a part of the path 'D:\…\<工作目录>\.github\workflows\checks.yml'`。
- 根因：`[System.IO.File]::ReadAllBytes('相对路径')` 用 PowerShell **进程启动目录**，不是 `Set-Location` 之后的目录。
- 做法：传绝对路径；`Get-ChildItem $_.FullName` 之类给的是绝对路径，安全。

## 7. push 之后 run 迟迟不出现

- 现象：合并到 main 后轮询数分钟，`gh run list` 与 `actions/runs?head_sha=` 都是 `total_count=0`。
- 根因：GitHub 侧的事件到 run 创建之间有延迟（实测数分钟）。
- 做法：按 head_sha 查询并耐心等；把「查不到」当成「延迟」而不是「没触发」。

## 8. `settings/branch_protection_rules` 是 404

- 现象：想直接看规则详情，打开的是 GitHub 404 插画页。
- 根因：没有这个路由。
- 做法：列表入口是 `settings/branches`，里面每个规则的 Edit 链接形如
  `settings/branch_protection_rules/<id>`——规则 ID 从这里拿。

## 9. 推送 base 分支不会重跑 PR 的 workflow

- 现象：把 workflow 合进 main，旧 PR 的 check 依然是失败/缺失。
- 根因：`pull_request` 事件只在 head 有推送时触发。
- 做法：`gh pr update-branch N`（需 `allow_update_branch=true`）或往 head 推一个空提交。

## 10. base64 内容按行解码成乱码

- 现象：`gh api .../contents/FILE --jq .content` 之后逐行解码，输出大量乱码。
- 根因：base64 内容带换行，逐行解码会把每行当独立 base64。
- 做法：一次性解码整串——`[Convert]::FromBase64String($raw -join '')`。

## 11. 工作区 CRLF 被当成缺陷

- 现象：本地核查报「文件含 CRLF」，但仓库里明明没有。
- 根因：本机 `core.autocrlf=true` 在检出时转换行尾；仓库存储仍是 LF。
- 做法：用 `git cat-file blob HEAD:<path>` 看**仓库存储**的真身；仓库没有 `.gitattributes` 时，
  Linux CI（autocrlf=false）不会触发该警告——把它写成提示而非失败。

## 12. 核查脚本全 PASS 却退出 1

- 现象：所有检查通过，CI 恒红。
- 根因：计数器用 `{level: 0 for level, _ in RESULTS}` 初始化，零 FAIL 时 `counts['FAIL']` 抛 `KeyError`。
- 做法：按完整级别集合初始化（`for level in ("PASS","FAIL","WARN","NOTE")`）。
  推论：核查脚本必须在本地实跑过一遍正向 + 一遍反向，再让它上 CI。

## 13. `community/profile` 说没有 issue template

- 现象：线上 `issues/new/choose` 已经渲染出四个模板，API 的 `files.issue_template` 仍是 `false`。
- 根因：该字段对 YAML 表单的检测口径与网页不同。
- 做法：以线上页面为准；API 字段只用来查「有没有」，不用来断言「对不对」。

## 14. 给单人仓开强制 PR 审核

- 现象：开了之后自己的 PR 再也合不进去。
- 根因：GitHub 不允许自己批准自己的 PR。
- 做法：单人仓的 `required_pull_request_reviews` 保持 `null`；需要把关就用必需状态检查
  （CI 是机器，不需要第二个人）。
