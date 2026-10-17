#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gh_repo_baseline.py — 仓库设置 / 分支保护的 采集 → 基线 → 校验 三件套。

只用 Python 标准库 + 已登录的 `gh` CLI（凭据交给 gh，本脚本不读 token、不写远端）。

三个子命令
----------
  snapshot <owner>/<repo> [-o out.json]
      采集单个仓库现状：仓库设置、默认分支保护、rulesets、工作流、社区健康度。
  survey <owner> [--repos a,b,c | --limit N] [-o out.json]
      巡视多个仓库，算出**公共基线**（所有被巡视仓库取值一致的项）与**逐项分布**。
      基线文件即可直接喂给 `check --baseline`。
  check <owner>/<repo> --baseline base.json [--show-ok] [--json]
      读回目标仓库并与基线逐项对比；有偏差 → 退出码 1 并列出偏差。

退出码：0 = 采集成功 / 与基线一致；1 = 采集失败或有偏差；2 = 用法错误。

设计纪律
--------
* 本脚本只做「读」——所有写操作由人/agent 显式执行 `gh api -X PUT/PATCH`，
  这样「应用」与「复核」是两条独立路径，复核才有意义。
* `survey` 的 common 只是**事实**（谁和谁一致），不是**建议**。哪些项该随大流、
  哪些项本就该因仓而异（wiki、license、topics），由看报告的人判断。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# 采集字段
# --------------------------------------------------------------------------- #

REPO_SETTING_FIELDS = (
    "default_branch",
    "visibility",
    "archived",
    "has_issues",
    "has_projects",
    "has_wiki",
    "has_discussions",
    "has_downloads",
    "allow_merge_commit",
    "allow_squash_merge",
    "allow_rebase_merge",
    "allow_auto_merge",
    "delete_branch_on_merge",
    "allow_update_branch",
    "web_commit_signoff_required",
    "topics",
)

PROTECTION_FLAGS = (
    "enforce_admins",
    "allow_force_pushes",
    "allow_deletions",
    "required_linear_history",
    "required_signatures",
    "required_conversation_resolution",
    "lock_branch",
    "allow_fork_syncing",
    "block_creations",
)

COMMUNITY_KEYS = (
    "readme",
    "contributing",
    "pull_request_template",
    "issue_template",
    "code_of_conduct",
    "license",
)

#: 每次采集都会变 / 本来就该因仓而异，参与分布统计但不参与基线一致性判定。
NON_BASELINE = frozenset({"repo", "collected_at", "workflows", "community.health_percentage"})


# --------------------------------------------------------------------------- #
# gh 调用层
# --------------------------------------------------------------------------- #

def _run(cmd: list[str], timeout: int = 90) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def gh_json(path: str):
    """返回 (数据, 错误文本)。失败时数据为 None。"""
    code, out, err = _run(["gh", "api", path])
    if code != 0:
        return None, (err or out or f"gh 退出码 {code}").strip()
    try:
        return json.loads(out), None
    except json.JSONDecodeError as exc:  # pragma: no cover - gh 正常时不会发生
        return None, f"gh 输出不是合法 JSON：{exc}"


def _short(text: str, limit: int = 140) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def repo_names(owner: str, limit: int) -> list[str]:
    code, out, err = _run(
        ["gh", "repo", "list", owner, "--limit", str(limit), "--json", "name", "--jq", ".[].name"]
    )
    if code != 0:
        raise SystemExit(f"列出 {owner} 的仓库失败：{_short(err or out)}")
    return [line.strip() for line in out.splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# 快照
# --------------------------------------------------------------------------- #

def snapshot(repo: str) -> dict:
    data, err = gh_json(f"repos/{repo}")
    if err:
        raise SystemExit(f"读取 {repo} 失败：{_short(err)}")

    settings: dict = {f: data[f] for f in REPO_SETTING_FIELDS if f in data}
    sec = data.get("security_and_analysis") or {}
    settings["security_and_analysis"] = (
        {k: (v or {}).get("status") for k, v in sorted(sec.items())} if sec else None
    )
    settings["license"] = (data.get("license") or {}).get("spdx_id")

    branch = data.get("default_branch") or "main"
    prot, perr = gh_json(f"repos/{repo}/branches/{branch}/protection")
    if prot is None:
        # 未保护：这些字段在 GitHub 侧不存在。写成 null 而不是省略，
        # 好让分布里出现的是「不适用×N」而不是噪声般的「<缺失>×N」。
        protection: dict = {"protected": False, "detail": _short(perr, 80)}
        protection.update({flag: None for flag in PROTECTION_FLAGS})
        protection["required_status_checks"] = None
        protection["required_pull_request_reviews"] = None
    else:
        protection = {"protected": True}
        for flag in PROTECTION_FLAGS:
            value = prot.get(flag)
            protection[flag] = value.get("enabled") if isinstance(value, dict) else bool(value)
        rsc = prot.get("required_status_checks")
        protection["required_status_checks"] = (
            None
            if rsc is None
            else {"strict": rsc.get("strict"), "contexts": sorted(rsc.get("contexts") or [])}
        )
        protection["required_pull_request_reviews"] = prot.get("required_pull_request_reviews") is not None

    rulesets, rerr = gh_json(f"repos/{repo}/rulesets")
    workflows, werr = gh_json(f"repos/{repo}/contents/.github/workflows")
    profile, cerr = gh_json(f"repos/{repo}/community/profile")

    return {
        "repo": repo,
        "collected_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "settings": settings,
        "default_branch": branch,
        "protection": protection,
        "rulesets_count": len(rulesets) if isinstance(rulesets, list) else None,
        "rulesets_error": None if isinstance(rulesets, list) else _short(rerr, 80),
        "workflows": sorted(f["name"] for f in workflows) if isinstance(workflows, list) else [],
        "community": (
            {
                "health_percentage": profile.get("health_percentage"),
                "files": {
                    k: (profile.get("files") or {}).get(k) is not None for k in COMMUNITY_KEYS
                },
            }
            if isinstance(profile, dict)
            else {"error": _short(cerr, 80)}
        ),
    }


def flatten(prefix: str, value, out: dict) -> None:
    """把嵌套快照压成点号路径 → 标量，便于逐项比对。列表压成稳定 JSON 串。"""
    if isinstance(value, dict):
        for key, item in value.items():
            flatten(f"{prefix}.{key}" if prefix else key, item, out)
    elif isinstance(value, list):
        out[prefix] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        out[prefix] = value


def flat_snapshot(repo: str) -> dict:
    flat: dict = {}
    flatten("", snapshot(repo), flat)
    return flat


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #

def cmd_snapshot(args) -> int:
    snap = snapshot(args.repo)
    text = json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"已写出快照：{args.output}")
    else:
        print(text)
    return 0


def cmd_survey(args) -> int:
    names = (
        [n.strip() for n in args.repos.split(",") if n.strip()]
        if args.repos
        else repo_names(args.owner, args.limit)
    )
    if not names:
        print("没有可巡视的仓库。", file=sys.stderr)
        return 1

    flats: dict[str, dict] = {}
    for name in names:
        full = name if "/" in name else f"{args.owner}/{name}"
        flats[full] = flat_snapshot(full)
        print(f"  已采集 {full}", file=sys.stderr)

    keys = sorted({k for flat in flats.values() for k in flat})
    distribution: dict[str, dict] = {}
    common: dict = {}
    for key in keys:
        seen: dict[str, int] = {}
        for flat in flats.values():
            value = flat.get(key, "<缺失>")
            seen[json.dumps(value, ensure_ascii=False, sort_keys=True)] = (
                seen.get(json.dumps(value, ensure_ascii=False, sort_keys=True), 0) + 1
            )
        distribution[key] = seen
        if key not in NON_BASELINE and "<缺失>" not in seen and len(seen) == 1:
            common[key] = json.loads(next(iter(seen)))

    baseline = {
        "owner": args.owner,
        "surveyed": sorted(flats),
        "surveyed_count": len(flats),
        "collected_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "common": common,
        "distribution": distribution,
    }
    text = json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")

    print(f"\n巡视 {len(flats)} 个仓库，公共基线 {len(common)} 项：")
    for key in sorted(common):
        print(f"  = {key}: {json.dumps(common[key], ensure_ascii=False)}")
    varying = [k for k in sorted(distribution) if k not in common and k not in NON_BASELINE]
    print(f"\n取值不一致（{len(varying)} 项，需人工判断该不该随大流）：")
    for key in varying:
        spread = ", ".join(f"{v}×{n}" for v, n in sorted(distribution[key].items()))
        print(f"  ~ {key}: {spread}")
    if args.output:
        print(f"\n基线已写出：{args.output}")
    return 0


def cmd_check(args) -> int:
    base_path = Path(args.baseline)
    if not base_path.is_file():
        print(f"基线文件不存在：{base_path}", file=sys.stderr)
        return 2
    try:
        baseline = json.loads(base_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"基线文件不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    common = baseline.get("common") or {}
    if not isinstance(common, dict):
        print(f"基线文件格式不对：common 应为对象，实际 {type(common).__name__}", file=sys.stderr)
        return 2
    if not common:
        print(f"基线文件里没有公共项（common 为空）：{base_path}", file=sys.stderr)
        return 2
    flat = flat_snapshot(args.repo)

    ok, bad, missing = [], [], []
    for key in sorted(common):
        expected = common[key]
        if key not in flat:
            missing.append(key)
        elif flat[key] == expected:
            ok.append(key)
        else:
            bad.append((key, flat[key], expected))

    if args.json:
        print(
            json.dumps(
                {
                    "repo": args.repo,
                    "baseline_from": baseline.get("surveyed", []),
                    "matched": ok,
                    "deviations": [{"key": k, "actual": a, "baseline": e} for k, a, e in bad],
                    "not_collected": missing,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"目标：{args.repo}")
        print(f"基线：{base_path}（巡视 {baseline.get('surveyed_count', '?')} 个仓库，"
              f"{len(common)} 项公共项）\n")
        if args.show_ok:
            for key in ok:
                print(f"  ✓ {key} = {json.dumps(common[key], ensure_ascii=False)}")
        for key, actual, expected in bad:
            print(f"  ✗ {key}: 实际 {json.dumps(actual, ensure_ascii=False)}"
                  f" ≠ 基线 {json.dumps(expected, ensure_ascii=False)}")
        for key in missing:
            print(f"  ? {key}: 本次未采集到（缺权限或字段已移除）")
        print(f"\n一致 {len(ok)} 项；偏差 {len(bad)} 项；未采集 {len(missing)} 项。")
        if not bad and not missing:
            print("结论：与基线完全一致。")
        else:
            print("结论：存在偏差——请逐项确认是「该改仓库」还是「该改基线」。")

    return 1 if (bad or missing) else 0


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gh_repo_baseline.py",
        description="GitHub 仓库设置 / 分支保护的采集-基线-校验（只读，写操作交给 gh api）。",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_snap = sub.add_parser("snapshot", help="采集单个仓库快照")
    p_snap.add_argument("repo", help="owner/name")
    p_snap.add_argument("-o", "--output", help="写出 JSON 文件")
    p_snap.set_defaults(func=cmd_snapshot)

    p_survey = sub.add_parser("survey", help="巡视多仓，算公共基线")
    p_survey.add_argument("owner")
    p_survey.add_argument("--repos", help="显式仓库清单（逗号分隔），不传则列出该 owner 的仓库")
    p_survey.add_argument("--limit", type=int, default=30, help="列出仓库的上限，默认 30")
    p_survey.add_argument("-o", "--output", help="写出基线 JSON")
    p_survey.set_defaults(func=cmd_survey)

    p_check = sub.add_parser("check", help="读回目标仓并与基线对比")
    p_check.add_argument("repo", help="owner/name")
    p_check.add_argument("--baseline", required=True, help="survey 产出的基线 JSON")
    p_check.add_argument("--show-ok", action="store_true", help="同时列出一致的项")
    p_check.add_argument("--json", action="store_true", help="输出机器可读的差异 JSON")
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
