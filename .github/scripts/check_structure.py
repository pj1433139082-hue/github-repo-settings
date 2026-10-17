#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓内一致性核查：本仓库文档里自称的规矩，由本文件逐条实测。

退出码：0 = 全部通过；1 = 有任意一项失败（逐项打印 ✗ 与原因）。

本地与 CI 跑的是同一份：

    python .github/scripts/check_structure.py

只依赖标准库 + pyyaml（仅用于解析 YAML）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - CI 会先装 pyyaml
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
SKILL_NAME = "github-repo-settings"

REQUIRED = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/workflows/checks.yml",
    ".github/scripts/check_structure.py",
    "scripts/gh_repo_baseline.py",
]
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".txt"}
TEXT_NAMES = {".gitignore", ".gitattributes", ".editorconfig", "LICENSE"}
SKIP_DIRS = {".git", "__pycache__"}
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")

fails: list[str] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}  {detail}".rstrip())
        fails.append(name)


def text_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix in {".pyc", ".png", ".jpg"}:
            continue
        if SKIP_DIRS & set(p.relative_to(ROOT).parts):
            continue
        if p.suffix in TEXT_SUFFIXES or p.name in TEXT_NAMES:
            out.append(p)
    return sorted(out)


def load_yaml(path: Path):
    """解析 YAML。PyYAML 按 YAML 1.1 把裸 `on:` 解析成布尔键 True，这里归一化回来。"""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in (True, False):
            if key in data:
                data["on" if key is True else "off"] = data.pop(key)
    return data


def check_files() -> None:
    print("\n[1/7] 必备文件")
    for rel in REQUIRED:
        ok(f"{rel} 存在", (ROOT / rel).is_file())
    refs = sorted((ROOT / "references").glob("*.md"))
    ok("references/ 至少 6 篇", len(refs) >= 6, f"实际 {len(refs)} 篇")


def check_frontmatter() -> None:
    print("\n[2/7] SKILL.md frontmatter")
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    ok("frontmatter 存在且以 --- 开头", m is not None)
    if not m:
        return
    fm = m.group(1)
    nm = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
    ds = re.search(r"^description:\s*(\S.*)$", fm, re.M)
    ok(f"name == {SKILL_NAME}", bool(nm) and nm.group(1) == SKILL_NAME,
       nm.group(1) if nm else "缺 name")
    ok("description 非空", bool(ds) and len(ds.group(1)) > 40,
       f"{len(ds.group(1))} 字符" if ds else "缺 description")


def check_markdown() -> None:
    print("\n[3/7] Markdown 结构与内链")
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        ok(f"{rel} 代码块成对", len(re.findall(r"^```", text, re.M)) % 2 == 0)
        bad = []
        for label, target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not (p.parent / target.split("#")[0]).exists():
                bad.append(f"{label}→{target}")
        ok(f"{rel} 相对内链可解析", not bad, ", ".join(bad))
    ok("全仓无空文件", all(p.stat().st_size > 0 for p in ROOT.rglob("*") if p.is_file()
                          and not (SKIP_DIRS & set(p.relative_to(ROOT).parts))))


def check_text_encoding() -> None:
    print("\n[4/7] 行尾与编码（本仓约定：纯 LF、UTF-8、无 BOM）")
    crlf, bom, undecodable = [], [], []
    for p in text_files():
        raw = p.read_bytes()
        rel = p.relative_to(ROOT).as_posix()
        if b"\r\n" in raw:
            crlf.append(rel)
        if raw.startswith(b"\xef\xbb\xbf"):
            bom.append(rel)
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            undecodable.append(rel)
    ok("无 CRLF 文件", not crlf, ", ".join(crlf))
    ok("无 BOM 文件", not bom, ", ".join(bom))
    ok("全部 UTF-8 可解码", not undecodable, ", ".join(undecodable))


def check_workflow() -> None:
    print("\n[5/7] CI workflow（必需状态检查的 context 由它产生）")
    if yaml is None:
        ok("pyyaml 可用", False, "未安装，无法校验 YAML")
        return
    path = ROOT / ".github/workflows/checks.yml"
    data = load_yaml(path)
    ok("workflow 可解析", isinstance(data, dict))
    triggers = data.get("on") if isinstance(data, dict) else None
    if isinstance(triggers, dict):
        ok("监听 pull_request（PR 上才会产生 check）", "pull_request" in triggers, str(triggers))
        push = triggers.get("push")
        ok("监听 push 到默认分支 main", isinstance(push, dict) and "main" in (push.get("branches") or []))
    else:
        ok("on 段是映射", False, str(triggers))
    jobs = data.get("jobs") if isinstance(data, dict) else None
    ok("存在 job: checks（分支保护里的 context 必须是 job 名）",
       isinstance(jobs, dict) and "checks" in jobs, str(list(jobs or [])))
    job = (jobs or {}).get("checks") or {}
    steps = job.get("steps") or []
    ok("job 至少两步（checkout + 核查）", len(steps) >= 2, f"{len(steps)} 步")
    perms = data.get("permissions") if isinstance(data, dict) else None
    ok("permissions.contents == read（最小权限）",
       isinstance(perms, dict) and perms.get("contents") == "read", str(perms))


def check_issue_templates() -> None:
    print("\n[6/7] issue 模板 / PR 模板")
    if yaml is None:
        return
    tdir = ROOT / ".github/ISSUE_TEMPLATE"
    config = load_yaml(tdir / "config.yml")
    ok("config.yml 可解析", isinstance(config, dict))
    if isinstance(config, dict):
        ok("blank_issues_enabled 是布尔", isinstance(config.get("blank_issues_enabled"), bool),
           str(config.get("blank_issues_enabled")))
        links = config.get("contact_links") or []
        ok("contact_links 非空", len(links) > 0, str(len(links)))
        for i, link in enumerate(links, 1):
            ok(f"contact_links[{i}] 三字段齐全且 url 为 https",
               all(k in link for k in ("name", "url", "about")) and str(link.get("url", "")).startswith("https://"),
               str(link))
    forms = [p for p in sorted(tdir.glob("*.yml")) if p.name != "config.yml"]
    ok("至少 1 份 issue 表单", len(forms) >= 1, f"{len(forms)} 份")
    for p in forms:
        data = load_yaml(p)
        ok(f"{p.name} 有 name/description/body",
           isinstance(data, dict) and all(k in data for k in ("name", "description", "body")))
        body = (data or {}).get("body") or []
        ids = []
        for el in body:
            t = el.get("type")
            if t == "markdown":
                ok(f"{p.name} markdown 元素不带 validations", "validations" not in el)
            elif t in {"input", "textarea", "dropdown", "checkboxes"}:
                ids.append(el.get("id"))
                ok(f"{p.name} {t} 元素有 id", bool(el.get("id")))
                if t == "dropdown":
                    opts = (el.get("attributes") or {}).get("options") or []
                    ok(f"{p.name} dropdown 选项非空", isinstance(opts, list) and len(opts) > 0)
            else:
                ok(f"{p.name} 元素 type 合法", False, f"未知 type={t!r}")
        ok(f"{p.name} id 唯一", len(ids) == len(set(ids)), str(ids))
    pr = ROOT / ".github/pull_request_template.md"
    ok("PR 模板非空", pr.is_file() and pr.stat().st_size > 200)


def check_script_contract() -> None:
    print("\n[7/7] 采集脚本契约")
    src = (ROOT / "scripts/gh_repo_baseline.py").read_text(encoding="utf-8")
    ok("脚本无第三方 import（只用标准库）",
       not re.search(r"^\s*(import|from)\s+(requests|httpx|yaml|click)\b", src, re.M))
    ok("脚本只发只读请求（无 -X 参数）",
       "gh api" in src and not re.search(r"[\"']-X[\"']", src))
    ok("三子命令齐全", all(k in src for k in ("snapshot", "survey", "check")))
    ok("用法错误返回 2（契约写进 docstring）", "2 = 用法" in src)
    try:
        compile(src, "gh_repo_baseline.py", "exec")
        ok("脚本可编译", True)
    except SyntaxError as exc:  # pragma: no cover
        ok("脚本可编译", False, f"{exc}")


def main() -> int:
    if ROOT.name != SKILL_NAME:
        print(f"  · 提示：检出目录名 {ROOT.name!r} ≠ {SKILL_NAME!r}（安装时应改回原名）")
    check_files()
    check_frontmatter()
    check_markdown()
    check_text_encoding()
    check_workflow()
    check_issue_templates()
    check_script_contract()
    print()
    if fails:
        print(f"结论：{len(fails)} 项未通过")
        return 1
    print("结论：全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
