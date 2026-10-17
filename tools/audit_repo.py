#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""脱敏审计器（M6 固化形态）：五步扫描，硬门命中即非零退出。

与 plan/06 R1「脱敏四步 + 产物扫描」逐项对应：

  第 1 步 姊妹表述扫描：系列前缀 token（**运行时实算自家名允许集**）+ 工作区姊妹目录名
  第 2 步 跟踪文件名扫描：.env / .key / secret / token / password / credential
  第 3 步 全文本内容扫描：个人标记 / 邮箱 / 密钥形态 / 本机绝对路径（**输出掩码化**）
  第 4 步 二进制样本扫描：ASCII 与 UTF-16LE 双编码；本仓预期 0 个二进制
  第 5 步 构建产物扫描：跟踪面不得含构建产物类文件；超阈值大文件复核

五条纪律（踩过/借鉴过的坑）：

1. **判据运行时实算**：系列前缀允许集、个人标记、姊妹目录名全部当场推导，源码零敏感字面量
   ——审计器源码自己也在扫描面内，写死字面量会被自身判红；模式一律片段拼接构造。
2. **输出掩码化**：不回显命中原文——审计报告本身不得成为二次泄漏源。
3. **扫描面非空自证**：跟踪文件数低于底线即报"空转"（exit 2），不静默通过。
4. **无 .git（源码 zip 解压树）**：退回文件系统遍历；提交元数据检查显式标"不适用"。
5. **浅克隆（只见 1 提交）**：提交元数据检查**显式报 INCOMPLETE**（exit 2），
   不冒充"历史已验"——"我没扫到东西"要大声说。

用法：py -X utf8 tools/audit_repo.py [--tracked-only] [--selftest]
退出码：0 全过（打印 DESENSITIZE_AUDIT_OK）/ 1 硬门命中 / 2 环境不支持或扫描面过小
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC_DIR = os.path.join(REPO, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from medreview.cli import _ensure_utf8_stdio  # noqa: E402 （与 CLI 入口同一编码护栏实现源）

SEP = chr(92)  # 反斜杠（运行时构造，防转义地狱）
SEP_RE = re.escape(SEP)
_BANG = chr(33)

# ---------------------------------------------------------------------------
# 第 1 步：系列前缀形态（如 "10-16-2-"）与内容中的完整系列名
# ---------------------------------------------------------------------------
_SERIES_PREFIX_RE = re.compile(r"^\d{2}-\d{2}(?:-\d)?-")
_FAMILY_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{2}-\d{2}(?:-\d)?-[a-z][a-z0-9]*(?:-[a-z0-9]+)*)(?![A-Za-z0-9])")

# ---------------------------------------------------------------------------
# 第 2 步：文件名硬门（片段拼接构造）
# ---------------------------------------------------------------------------
_FILENAME_HARD = re.compile(
    r"(^|[/.])\.env$|\.key$|\.pem$|" + "secret" + "|" + "token" + r"|password|credential",
    re.I)

# ---------------------------------------------------------------------------
# 第 3 步：文本内容模式（全部片段拼接构造；noreply / 传输地址为合规豁免）
# ---------------------------------------------------------------------------
_DASH = "-"
_AT = "@"
TEXT_PATTERNS = {
    "email": re.compile(
        "[A-Za-z0-9._%+" + _DASH + "]+" + _AT + "[A-Za-z0-9." + _DASH + "]+[.][A-Za-z]{2,}"),
    "github_token": re.compile("gh" + "[a-z]" + "_" + "[A-Za-z0-9]{20,}"),
    "openai_style_key": re.compile("sk" + _DASH + "[A-Za-z0-9]{10,}"),
    "aws_access_key": re.compile("AK" + "IA" + "[0-9A-Z]{16}"),
    "phone_cn": re.compile(r"(?<![0-9a-fA-F])1[3-9][0-9]{9}(?![0-9a-fA-F])"),
    "id_card": re.compile(r"(?<![0-9a-fA-F])[0-9]{17}[0-9Xx](?![0-9a-fA-F])"),
    "win_abs_path": re.compile(
        "[A-Za-z]:" + SEP_RE + "(?:Users|ProgramData|workspace|Workspace)" + SEP_RE),
    "gitbash_abs_path": re.compile(r"(?<![A-Za-z0-9])/[a-z]/(?:[A-Za-z0-9_.-]+/){1,3}"),
}

# 合规豁免：noreply 是**脱敏目标形态**；git/ssh/hg 是传输地址，不是个人邮箱
_EMAIL_ALLOW = re.compile(
    "(" + _AT + "users[.]noreply[.]github[.]com$)|(^(?:git|ssh|hg)" + _AT + "[A-Za-z0-9." + _DASH + "]+$)")

# ---------------------------------------------------------------------------
# 第 5 步：构建产物形态（跟踪面命中即红）
# ---------------------------------------------------------------------------
_ARTIFACT_PATTERNS = [
    (re.compile(r"(^|/)__pycache__/"), "python 字节码缓存"),
    (re.compile(r"\.py[co]$"), "python 字节码"),
    (re.compile(r"\.egg-info/|\.egg-link$|\.egg$"), "打包元数据"),
    (re.compile(r"(^|/)dist/|(^|/)build/"), "dist/build 目录"),
    (re.compile(r"(^|/)\.pytest_cache/"), "pytest 缓存"),
    (re.compile(r"(^|/)\.venv"), "venv 目录"),
    (re.compile(r"(^|/)\.tmp/"), "临时产物目录"),
    (re.compile(r"\.(so|dll|exe|dylib)$"), "本机二进制库"),
    (re.compile(r"\.(zip|bundle|log)$"), "打包/日志产物"),
    (re.compile(r"(^|/)\.coverage$|\.DS_Store$"), "覆盖/系统产物"),
]
_LARGE_FILE_BYTES = 2_000_000

_SKIP_DIRS = (".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
              ".ruff_cache", ".tmp", "dist", "build")
_SCAN_FLOOR = 40


def _run(args, binary=False):
    proc = subprocess.run(["git", "-c", "core.quotepath=off"] + list(args),
                          cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if binary:
        return proc.returncode, proc.stdout
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def _is_git_tree():
    return os.path.isdir(os.path.join(REPO, ".git"))


def _tracked_files():
    """扫描面清单（相对路径，正斜杠）；**无 git 兜底**：导出树退回文件系统遍历。"""
    if _is_git_tree():
        rc, listing = _run(["ls-files"])
        if rc == 0:
            names = [f for f in listing.splitlines() if f.strip()]
            if names:
                return names, "git ls-files"
    names = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS and not d.endswith(".egg-info")]
        if "pyvenv.cfg" in filenames:
            continue
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, REPO).replace(os.sep, "/")
            names.append(rel)
    return sorted(names), "filesystem walk (无 .git 兜底)"


def _read_bytes(name):
    try:
        with open(os.path.join(REPO, name.replace("/", os.sep)), "rb") as handle:
            return handle.read()
    except OSError:
        return None


def _decode_text(raw):
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _mask(value):
    value = value.replace(SEP, "/")
    if len(value) <= 8:
        return value[:1] + "*" * max(len(value) - 1, 1)
    return value[:4] + "*" * 4 + value[-2:]


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _own_names():
    """自家名允许集（运行时实算，**数据驱动**）：README 自指 URL 的仓库名 + 本地目录名。

    判据落仓库内容而非目录名——干净 clone / 导出树的目录名不等于仓库名
    （实测：clone 到 cleanclone 时按目录名推导会让自家 badge URL 误报）。
    """
    own_clean = os.path.basename(REPO)
    own_local = os.path.basename(os.path.abspath(REPO))
    for probe in ("README.md", "SKILL.md", "pyproject.toml"):
        raw = _read_bytes(probe)
        if raw is None:
            continue
        text = _decode_text(raw) or raw.decode("utf-8", "replace")
        match = re.search(r"github\.com/[A-Za-z0-9-]+/([A-Za-z0-9._-]+)", text)
        if match:
            own_clean = match.group(1)
            break
    return own_local, own_clean


def _sibling_tokens():
    """工作区姊妹目录名（运行时从父目录推导；CI 检出目录下通常为空）。

    两种形态都扫：带系列前缀的原名 + 去前缀的 kebab 名。
    自家名（目录名 / README 自指仓库名 / 各自去前缀变体）一律排除。
    """
    parent = os.path.dirname(REPO)
    own_local, own_clean = _own_names()
    allowed = {own_local, own_clean, _SERIES_PREFIX_RE.sub("", own_local),
               _SERIES_PREFIX_RE.sub("", own_clean)}
    tokens = set()
    try:
        entries = sorted(os.listdir(parent))
    except OSError:
        return []
    for entry in entries:
        if entry.startswith(".") or entry in allowed:
            continue
        if not _SERIES_PREFIX_RE.match(entry):
            continue
        stripped = _SERIES_PREFIX_RE.sub("", entry)
        if stripped and stripped not in allowed and len(stripped) >= 4:
            tokens.add(entry)
            tokens.add(stripped)
        else:
            tokens.add(entry)
    return sorted(tokens)


def _personal_literals():
    """本机个人/工作区标记（运行时实算，不写死字面量）。"""
    markers = []
    home = os.path.expanduser("~")
    user = os.path.basename(home.rstrip("/" + SEP)) if home else ""
    if user:
        markers.append(("用户目录签名", "Users" + SEP + user))
        markers.append(("用户目录签名(fwd)", "Users/" + user))
    parent_name = os.path.basename(os.path.dirname(REPO))
    repo_name = os.path.basename(REPO)
    if parent_name:
        markers.append(("工作区路径签名", parent_name + SEP + repo_name))
        markers.append(("工作区路径签名(fwd)", parent_name + "/" + repo_name))
    return markers


def _series_hits_in(value):
    """系列名检查：自家名允许（原名或去前缀变体）；其余系列形态 = 命中。"""
    hits = []
    own_local, own_clean = _own_names()
    allowed = {own_local, own_clean, _SERIES_PREFIX_RE.sub("", own_local)}
    for match in _FAMILY_RE.finditer(value):
        token = match.group(1)
        if _SERIES_PREFIX_RE.sub("", token) in allowed:
            continue
        hits.append((token, match.start()))
    return hits


def _sibling_hits_in(value, tokens):
    hits = []
    lowered = value.lower()
    for token in tokens:
        pos = value.find(token)
        if pos < 0:
            pos = lowered.find(token.lower())
        if pos >= 0:
            hits.append((token, pos))
    return hits


def scan_sister_expressions(files):
    """第 1 步：姊妹表述扫描（文件名 + 文本内容）。"""
    tokens = _sibling_tokens()
    hits = []
    scanned = 0
    for name in files:
        scanned += 1
        for token, _pos in _series_hits_in(name):
            hits.append(("step1_name", name, "系列名形态 %s" % _mask(token)))
        for token, _pos in _sibling_hits_in(name, tokens):
            hits.append(("step1_name", name, "姊妹目录名 %s" % _mask(token)))
        raw = _read_bytes(name)
        if raw is None:
            continue
        text = _decode_text(raw)
        if text is None:
            continue
        for token, pos in _series_hits_in(text):
            hits.append(("step1_content", "%s:%d" % (name, _line_of(text, pos)),
                         "系列名形态 %s" % _mask(token)))
        for token, pos in _sibling_hits_in(text, tokens):
            hits.append(("step1_content", "%s:%d" % (name, _line_of(text, pos)),
                         "姊妹目录名 %s" % _mask(token)))
    return scanned, len(tokens), hits


def scan_filenames(files):
    """第 2 步：跟踪文件名扫描。"""
    hits = []
    for name in files:
        base = name.rsplit("/", 1)[-1]
        if _FILENAME_HARD.search(base):
            hits.append(("step2_filename", name, "文件名命中敏感形态"))
        elif _FILENAME_HARD.search(name):
            hits.append(("step2_filename", name, "路径命中敏感形态"))
    return hits


def scan_text_content(files):
    """第 3 步：全文本内容扫描（掩码输出）。"""
    hits = []
    scanned = 0
    markers = _personal_literals()
    for name in files:
        raw = _read_bytes(name)
        if raw is None:
            continue
        text = _decode_text(raw)
        if text is None:
            continue
        scanned += 1
        for pname, pattern in TEXT_PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0)
                if pname == "email" and _EMAIL_ALLOW.search(value):
                    continue
                hits.append(("step3_content", "%s:%d" % (name, _line_of(text, match.start())),
                             "%s %s" % (pname, _mask(value))))
        for mname, literal in markers:
            pos = text.find(literal)
            if pos >= 0:
                hits.append(("step3_content", "%s:%d" % (name, _line_of(text, pos)),
                             "%s %s" % (mname, _mask(literal))))
    return scanned, hits


def scan_binary(files):
    """第 4 步：二进制样本扫描（ASCII + UTF-16LE 双编码；输出掩码化）。"""
    hits = []
    scanned = 0
    markers = _personal_literals()
    for name in files:
        raw = _read_bytes(name)
        if raw is None or b"\x00" not in raw:
            continue
        scanned += 1
        for mname, literal in markers:
            for enc in ("ascii", "utf-16-le"):
                try:
                    needle = literal.encode(enc)
                except UnicodeEncodeError:
                    continue
                if needle in raw:
                    hits.append(("step4_binary", name, "%s (%s)" % (mname, enc)))
        for token, _pos in _series_hits_in(raw.decode("utf-8", "replace")):
            hits.append(("step4_binary", name, "系列名形态 %s" % _mask(token)))
    return scanned, hits


def scan_artifacts(files):
    """第 5 步：构建产物扫描（跟踪面 + 大文件复核 + 忽略面简报）。"""
    hits = []
    largest = ("", 0)
    for name in files:
        for pattern, label in _ARTIFACT_PATTERNS:
            if pattern.search(name):
                hits.append(("step5_artifact", name, label))
                break
        size = len(_read_bytes(name) or b"")
        if size > largest[1]:
            largest = (name, size)
    big = [n for n in files if len(_read_bytes(n) or b"") > _LARGE_FILE_BYTES]
    info = {"largest": largest, "over_threshold": big}
    ignored_note = ""
    if _is_git_tree():
        rc, status = _run(["status", "--porcelain", "--ignored"])
        if rc == 0:
            ignored = [ln for ln in status.splitlines() if ln.startswith(_BANG + _BANG)]
            ignored_note = "忽略面 %d 项（.gitignore 覆盖，不入跟踪面）" % len(ignored)
    return hits, info, ignored_note


def scan_commit_metadata(tracked_only):
    """提交元数据检查：邮箱 + 提交信息内容扫描。

    返回 (status, emails, hits)；status ∈ {"ok", "shallow", "no_git", "skipped"}。
    """
    if tracked_only:
        return "skipped", [], []
    if not _is_git_tree():
        return "no_git", [], []
    rc, count_out = _run(["rev-list", "--all", "--count"])
    if rc != 0:
        return "no_git", [], []
    count = int(count_out.strip() or "0")
    if count == 0:
        return "shallow", [], []
    if count == 1:
        return "shallow", [], []
    hits = []
    emails = set()
    rc, out = _run(["log", "--all", "--format=%ae%n%ce"])
    if rc != 0:
        return "shallow", [], []
    for token in out.splitlines():
        if _AT in token:
            emails.add(token.strip())
    for email in sorted(emails):
        if _EMAIL_ALLOW.search(email):
            continue
        hits.append(("commit_email", "(提交元数据)", "非 noreply 邮箱 %s" % _mask(email)))
    rc, messages = _run(["log", "--all", "--format=%s%n%b"])
    if rc == 0:
        for pname, pattern in TEXT_PATTERNS.items():
            for match in pattern.finditer(messages):
                value = match.group(0)
                if pname == "email" and _EMAIL_ALLOW.search(value):
                    continue
                hits.append(("commit_message", "(提交信息)", "%s %s" % (pname, _mask(value))))
        for token, _pos in _series_hits_in(messages):
            hits.append(("commit_message", "(提交信息)", "系列名形态 %s" % _mask(token)))
    return "ok", sorted(emails), hits


def selftest():
    """阳性 + 阴性对照：扫描机制必须真能命中，合规形态不得误报。

    合成串一律**运行时拼接构造**——审计器源码自己也在扫描面内。
    """
    fake_phone = "139" + "0000" + "0000"
    fake_key = "gh" + "p" + "_" + "A" * 36
    fake_mail = "user" + _AT + "example" + ".org"
    fake_path = "C" + ":" + SEP + "Users" + SEP + "alice"
    fake_family = "10" + "-99" + "-9-" + "fake-project"
    positive = " ".join([fake_phone, fake_key, fake_mail, fake_path, fake_family])
    for pname in ("phone_cn", "github_token", "email", "win_abs_path"):
        assert TEXT_PATTERNS[pname].search(positive), \
            "阳性对照未命中 %s → 扫描器坏了" % pname
    # 系列名检查：非自家系列名必须判为命中
    assert _series_hits_in(fake_family), "阳性对照未命中系列名形态 → 扫描器坏了"
    # 阴性对照：自家名（README 自指形态 / 本地目录名形态 / 各自去前缀变体）不得误报
    own_local, own_clean = _own_names()
    own_variants = [own_clean, own_local,
                    _SERIES_PREFIX_RE.sub("", own_clean),
                    _SERIES_PREFIX_RE.sub("", own_local)]
    for value in own_variants:
        assert not _series_hits_in(value), "自家名被误报：%s" % value
    # 阴性对照：noreply / 传输地址不得判为个人邮箱
    for safe in ("282769740+yuluo554" + _AT + "users.noreply.github.com",
                 "git" + _AT + "github.com"):
        assert _EMAIL_ALLOW.search(safe), "合规邮箱被误报：%s" % safe
    assert not _EMAIL_ALLOW.search(fake_mail), "真邮箱被误豁免"
    # 第 5 步对照：普通源码路径不得误报，产物形态必须命中
    probe = "src/medreview/cli.py"
    assert not any(p.search(probe) for p, _ in _ARTIFACT_PATTERNS), "源码路径被误报"
    artifact_probe = "__pycache__" + "/x.pyc"
    assert any(p.search(artifact_probe) for p, _ in _ARTIFACT_PATTERNS), \
        "产物形态未命中 → 扫描器坏了"
    return 0


def main(argv=None):
    _ensure_utf8_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    tracked_only = "--tracked-only" in argv
    selftest_only = "--selftest" in argv

    selftest()
    print("[audit] selftest: OK（阳性对照命中；自家名/noreply/源码路径正确豁免）")
    if selftest_only:
        print("DESENSITIZE_AUDIT_OK")
        return 0

    files, source = _tracked_files()
    print("[audit] 仓库：%s" % os.path.basename(REPO))
    print("[audit] 扫描面来源：%s" % source)
    print("[audit] 第1步 姊妹表述扫描：%d 个文件名 + 文本内容（姊妹 token %d 个，运行时实算）"
          % (len(files), len(_sibling_tokens())))
    if len(files) < _SCAN_FLOOR:
        print("[audit] 结论：INCOMPLETE（跟踪面过小：%d < %d，疑似空转）" % (len(files), _SCAN_FLOOR))
        return 2

    hits = []
    _s1, _tok, s1_hits = scan_sister_expressions(files)
    hits.extend(s1_hits)
    hits.extend(scan_filenames(files))
    print("[audit] 第2步 跟踪文件名扫描：%d 个文件" % len(files))
    text_scanned, s3_hits = scan_text_content(files)
    hits.extend(s3_hits)
    print("[audit] 第3步 全文本内容扫描：%d 个文本文件" % text_scanned)
    if text_scanned < _SCAN_FLOOR:
        print("[audit] 结论：INCOMPLETE（文本扫描面过小：%d < %d）" % (text_scanned, _SCAN_FLOOR))
        return 2
    bin_scanned, s4_hits = scan_binary(files)
    hits.extend(s4_hits)
    print("[audit] 第4步 二进制样本扫描：%d 个二进制文件" % bin_scanned)
    s5_hits, info, ignored_note = scan_artifacts(files)
    hits.extend(s5_hits)
    print("[audit] 第5步 构建产物扫描：最大文件 %s（%d 字节）；超阈值 %d 个%s"
          % (info["largest"][0], info["largest"][1], len(info["over_threshold"]),
             ("；" + ignored_note) if ignored_note else ""))

    status, emails, meta_hits = scan_commit_metadata(tracked_only)
    hits.extend(meta_hits)
    if status == "ok":
        print("[audit] 提交元数据邮箱：%s" % (", ".join(_mask(e) for e in emails) or "(无)"))
    elif status == "shallow":
        print("[audit] 提交元数据检查：**浅克隆（只见 1 提交）无法成立**——显式 INCOMPLETE")
        return 2
    elif status == "no_git":
        print("[audit] 提交元数据检查：不适用（导出树、无 .git）")
    else:
        print("[audit] 提交元数据检查：skipped (--tracked-only)")

    for step, where, what in hits:
        print("  [HIT] %s %s <- %s" % (step, where, what))
    if hits:
        print("[audit] 结论：FAIL（%d 处硬门命中）" % len(hits))
        return 1
    print("[audit] 结论：PASS（0 硬门命中）")
    print("DESENSITIZE_AUDIT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
