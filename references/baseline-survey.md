# 基线巡视：把「公共设置」当事实测出来

## 巡视对象怎么选

- 同一个 owner 下的**活跃**仓库。`survey OWNER` 默认列出全部；更精确时用 `--repos a,b,c`。
- 排除 fork 和 archived——它们的设置不是任何人有意选的。
- 想回答「这套设置长什么样」时，巡视**同类**仓库；想回答「我该随哪个大流」时，巡视**全部**仓库。两者会给出不同宽度的基线。
  实测差异：15 个仓库全巡 → 14 项公共项；只巡 2 个已保护仓库 → 43 项公共项。

## 读输出

```
= key: value        所有被巡视仓库取值一致 → 进了 common
~ key: v1×12, v2×3  取值不一致 → 只在 distribution 里
```

`common` 是**事实**（谁和谁一致），不是**建议**。判定哪些项该随大流：

| 该随大流 | 本就该因仓而异 |
|---|---|
| `has_issues` / `has_projects` / `has_discussions` | `license`、`has_wiki`、`topics`、`visibility` |
| `allow_*_merge`、`delete_branch_on_merge` | `security_and_analysis`（private 仓读不到，会显示为缺失） |
| 分支保护的各个 flag | `community.files.*`（新仓还没写，缺是正常的） |
| `web_commit_signoff_required` | `allow_update_branch`（取决于是否多人协作） |

一条实用判据：**看分布里的少数派能不能被解释。** `has_wiki: false×13, true×2` 能解释（那 2 个确实在用 wiki）
就该随大流；`has_issues: false×1` 解释不了就单独查那个仓为什么。

## 别把「已保护仓的样子」当成「所有仓该有的样子」

巡视 2 个已保护仓库会得到 `protection.protected: true` 这种公共项。
把它套到第 3 个未保护的仓库上，`check` 会报 13 条 `protection.*` 偏差——这**不是脚本出错**，
而是基线本来就该按用途分组。要做「照着 A 配 B」，巡视对象就只放和 B 同类的仓。

## 基线文件

```json
{
  "owner": "...", "surveyed": ["owner/a", "owner/b"], "surveyed_count": 2,
  "common": { "settings.has_wiki": false, "protection.allow_force_pushes": false },
  "distribution": { "settings.has_wiki": { "false": 1, "true": 1 } }
}
```

`common` 的键是**点号路径**，值是 JSON 标量；列表（如 `topics`、`contexts`）压成稳定排序的 JSON 串，
所以可以直接当字典键比较。不参与一致性判定的键：`repo`、`collected_at`、`workflows`、`community.health_percentage`
（本来就每次都不同）。

## 把它当回归基线长期用

把基线文件提交进仓库（例如 `.github/repo-baseline.json`），CI 里跑：

```bash
python3 scripts/gh_repo_baseline.py check "$GITHUB_REPOSITORY" --baseline .github/repo-baseline.json
```

`check` 会**重新采集**而不是回显，所以能抓到「有人手工在 UI 上把设置改回去了」。
每次有意变更设置后同步更新基线文件，这样偏差永远等于「没被批准的变更」。
