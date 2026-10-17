# 验证：怎么知道它真的生效了

「写进去了」「生效了」「用户看到了」是三件不同的事，各有各的证据。

## 第一重：API 读回

```bash
gh api repos/O/R/branches/BRANCH                    # protected: true/false
gh api repos/O/R/branches/BRANCH/protection         # 逐字段
gh api repos/O/R | jq '{has_wiki, has_issues, delete_branch_on_merge}'
python3 scripts/gh_repo_baseline.py check O/R --baseline base.json
```

**读回必须是独立的一次请求**，不能是回显你刚写出去的 payload——回显只能证明你发过请求。
`check` 子命令每次重新采集，这正是它的价值。

写成功不等于写对：`PUT` 是整包替换，漏字段会被静默重置。所以读回要逐字段比对，而不是只看 200。

## 第二重：浏览器实测（用户视角）

API 说「横幅不该出现」和用户说「横幅没了」之间隔着渲染与缓存。用真实浏览器确认那一次：

```
opencli browser <session> open <url> --window background
opencli browser <session> extract
```

- 版本事实：opencli 1.8.7 的 `screenshot` 子命令会报
  `The first argument must be of type string or an instance of Buffer… Received an instance of Object`，
  任何路径形式都一样；用 `extract`（正文 markdown）或 `state`（DOM 转储）替代。
- `extract` 的返回里正文在 `content` 字段，且是转义过的 JSON 字符串——解析时先取 `{` 起始再 `ConvertFrom-Json`。
- URL 事实：分支保护列表的正确入口是 `settings/branches`；
  `settings/branch_protection_rules` 会 404（返回 GitHub 的 404 插画页）。
- 没有 `opencli` 时退化为人工：浏览器打开页面看横幅 / 链接是否如预期，截图留证；
  「门禁有没有拦人」只看 `gh pr view N --json mergeStateStatus`（`BLOCKED` / `CLEAN`）。

浏览器这一步还能抓到 API 抓不到的东西：**渲染层截断**。曾出现 contact link 的
`name` 与 `about` 在网页上被截到一半，而 API 解析成功、行数不变——因为 YAML 把 ` #` 之后当注释吃掉了。
只有把页面抓下来看才发现的。

## 第三重：行为证据

设置类改动的终极证据是「它真的拦了一次」：

- 必需状态检查 → 让 `mergeStateStatus` 从 `BLOCKED` 变成 `CLEAN`。
- 禁强推 / 禁删除 → 这类不便真去试（会污染历史），改用逐字段读回 + `enforce_admins` 的取值说明清楚。

## 报告纪律

把结果分两栏写：

```
已核实：main 分支保护 ruleset 生效（gh api …/branches/main → protected: true，规则 ID `<ruleset-id>`）
未核实：非维护者视角的权限表现（没有第二个账号）
```

每条「已核实」后面附上产生它的命令或日志行；**未运行的检查就写「未运行」，不写「通过」**。

## 编写本技能时踩到的四条假完成

1. 没验证就写下「`/security/advisories/new` 会 404」——实际维护者能看到草稿页，`enabled: false` 是另一回事。
2. 以为「把 workflow 合进 main 就会让旧 PR 重跑」——`pull_request` 事件只认 head 分支的推送。
3. 看到日志里有 `echo "::notice …"` 就以为兜底分支执行了——那只是 GitHub 回显的脚本文本。
4. 自己的核查脚本「全 PASS 却退出 1」（计数器字典在零 FAIL 时 `KeyError`）——差点把恒红的 CI 推上去。

共同点：**都是「推理出来的结论」被当成了「观察到的结论」**。补一次实跑，四条全部现形。
