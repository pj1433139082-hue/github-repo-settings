# 参与贡献

这是一个面向智能体（agent）的 GitHub 仓库设置技能：`SKILL.md` 是给智能体读的流程，`references/` 是字段全表与踩坑，`scripts/` 里有一个只读的采集/基线/校验脚本。

## 仓库结构

```
SKILL.md                    主流程：分类 → 六步 → 四条硬纪律 → 边界
references/                 6 篇：基线判定、分支保护、社区健康、CI 门禁、三重验证、踩坑
scripts/gh_repo_baseline.py snapshot / survey / check 三件套（只 import 标准库）
.github/
  workflows/checks.yml      唯一 CI：结构核查 + 脚本契约
  scripts/check_structure.py 仓内一致性核查（本地和 CI 是同一份）
  ISSUE_TEMPLATE/           issue 表单（config.yml 关掉了空白 issue）
  pull_request_template.md  PR 模板
```

## 本地开发

无第三方运行时依赖；跑核查需要 `pyyaml`。

```bash
# 1. 结构核查（退出码 0 才可提交）
python -m pip install --quiet pyyaml
python .github/scripts/check_structure.py
# 预期最后一行：结论：全部通过

# 2. 采集脚本能否起来
python scripts/gh_repo_baseline.py --help
# 预期：打印三个子命令，退出码 0

# 3. 退出码契约
python scripts/gh_repo_baseline.py check octocat/Hello-World --baseline /nonexistent.json
# 预期：退出码 2（用法/输入问题），而不是 0 或 1
```

Windows 下把 `python3` 换成 `python`；`check_structure.py` 会拒绝 CRLF 文件，编辑器请设 `end_of_line = lf`（仓根已有 `.editorconfig`）。

### 反向测试

「正常时是绿的」不等于核查有效。改动核查逻辑时，故意弄坏一处再跑，确认它真的退出 1，例如：

```bash
cp -r . /tmp/ghrs && cd /tmp/ghrs
printf 'name: wrong-name\n' > SKILL.md    # 故意破坏 frontmatter
python .github/scripts/check_structure.py; echo "exit=$?"   # 预期 exit=1
```

## 提交与分支

- 分支：`main` 受保护，必须走 PR；不能用 `git push` 直接推 `main`（管理员可绕过，但请别绕）。
- 提交信息：Conventional Commits 风格，如 `docs: 补充 ruleset 与经典保护的取舍`、`fix(script): survey 在 API 中断时不再写半份基线`。
- 合并方式：squash merge。合并后源分支自动删除。
- PR 必须通过 CI 的 `checks` 这项必需状态检查。

## 改动边界

- 只改与本次问题相关的行；不给文档做无关重排。
- `references/` 里的事实性断言（GitHub 行为、API 端点、字段名）要能在 `gh api` 里复核；改之前先跑一遍。
- 已知限制清单在 `README.md` 的「已知限制」小节，新增限制请同步补进去。
- 涉及许可证与行为准则的改动：本仓库目前**没有** `CODE_OF_CONDUCT.md`，也不打算默认加——这类文件涉及对外治理承诺，先开 issue 讨论。

## 报告问题

用 issue 表单（blank issue 已关闭）。安全漏洞请走 [私有漏洞报告](https://github.com/pj1433139082-hue/github-repo-settings/security/advisories/new)，见 `SECURITY.md`。
