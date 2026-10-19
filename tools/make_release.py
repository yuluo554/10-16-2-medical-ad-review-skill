#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发布物打包器（M6 固化形态）：确定性源码 zip + sha256 台账。

确定性配方（同一 tree-ish 在任意平台、任意 Python 两次构建**逐字节一致**）：

  · 打包面 = git 跟踪面：``--rev`` 指定 tree-ish（发布时传 tag，保证附件与 tag 树同源）；
    缺省取当前 HEAD 提交树。
  · ``ZIP_STORED``（不压缩）+ 条目按路径 UTF-8 字节序排序 + 全部条目固定 ``date_time``
    + 固定 ``create_system``（跨平台一致）+ 固定外部属性（0644，保留可执行位 0755）。
  · ``core.quotepath=off`` 防中文文件名八进制转义。
  · 无 ``.git``（源码 zip 解压树）时退回文件系统遍历——便于"下载件 → 解包 → 重打包比对"。

自指规避（发布留档的既定口径）：
  附件 zip 内含仓库文件，故 **zip 自身的 sha256 不写入 zip 内的任何文件**（写入即自指、
  永不成立）。台账 ``plan/DIST-sha256-M6.txt`` 随**发布后回填提交**落 main 分支；
  zip 内的本工具与 RELEASE 留档只写"复算规则"，不复录结果值。

用法：
    py -X utf8 tools/make_release.py --rev v0.1.0 --out <path.zip> [--ledger <path.txt>]
    py -X utf8 tools/make_release.py --verify <path.zip> --rev v0.1.0
退出码：0 OK（打印 ZIP_BUILD_OK / ZIP_VERIFY_OK）/ 1 校验不一致 / 2 环境或用法错误
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC_DIR = os.path.join(REPO, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from medreview.cli import _ensure_utf8_stdio  # noqa: E402 （与 CLI 入口同一编码护栏实现源）

# 固定为发布基准日（改版发布时随版本更新；固定值 = 可复现打包的第一要件）
FIXED_DATE_TIME = (2026, 10, 20, 0, 0, 0)

_MODE_EXEC = 0o100755
_MODE_FILE = 0o100644
_SKIP_DIRS = (".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
              ".ruff_cache", ".tmp", "dist", "build")
_CREATE_SYSTEM_UNIX = 3  # 固定 3（unix），跨平台字节一致


def _git(args):
    proc = subprocess.run(["git", "-c", "core.quotepath=off"] + list(args),
                          cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", "replace")


def _is_git_tree():
    return os.path.isdir(os.path.join(REPO, ".git"))


def _resolve_rev(rev):
    rc, out, err = _git(["rev-parse", "--verify", rev + "^{tree}"])
    if rc != 0:
        raise RuntimeError("无法解析 rev %s：%s" % (rev, err.strip()))
    return out.decode("ascii").strip()


def _list_tree(rev):
    """返回 [(mode, path)]：git 跟踪面，按路径 UTF-8 字节序排序。"""
    rc, out, err = _git(["ls-tree", "-r", "-z", rev])
    if rc != 0:
        raise RuntimeError("git ls-tree 失败：%s" % err.strip())
    entries = []
    for record in out.split(b"\x00"):
        if not record.strip():
            continue
        meta, path = record.split(b"\t", 1)
        mode, otype, _sha = meta.decode("ascii").split(" ")
        if otype != "blob":
            continue
        entries.append((int(mode, 8), path.decode("utf-8")))
    entries.sort(key=lambda item: item[1].encode("utf-8"))
    return entries


def _list_filesystem():
    """无 git 兜底：导出树文件系统遍历（跳过 venv/缓存/构建目录，不按名字猜文件）。"""
    entries = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS and not d.endswith(".egg-info")
                       and not d.startswith(".venv") and d != "venv"
                       and not d.startswith("venv.")]
        if "pyvenv.cfg" in filenames:
            continue
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, REPO).replace(os.sep, "/")
            entries.append((_MODE_FILE, rel))
    entries.sort(key=lambda item: item[1].encode("utf-8"))
    return entries


def _read_blob(rev, path):
    rc, out, err = _git(["cat-file", "blob", "%s:%s" % (rev, path)])
    if rc != 0:
        raise RuntimeError("读取 blob 失败 %s:%s：%s" % (rev, path, err.strip()))
    return out


def build_zip_bytes(rev):
    """按确定性配方构建 zip 字节。

    rev 为 None 或（``"HEAD"`` 且无 ``.git``，即源码 zip 解压树）时走文件系统
    遍历兜底——"下载件 → 解包 → 重打包比对"是发布物复核的常用形态，
    依赖 git 的打包器在无 ``.git`` 树里会直接崩（同类工具的发布期实录）。
    """
    if rev == "HEAD" and not _is_git_tree():
        rev = None
    if rev is None:
        entries = _list_filesystem()
        rev_label = "(filesystem walk, 无 .git 兜底)"
    else:
        entries = _list_tree(rev)
        rev_label = rev
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        for mode, path in entries:
            if rev is None:
                data = open(os.path.join(REPO, path.replace("/", os.sep)), "rb").read()
            else:
                data = _read_blob(rev, path)
            info = zipfile.ZipInfo(filename=path, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = _CREATE_SYSTEM_UNIX
            info.external_attr = (_MODE_EXEC if (mode & 0o111) else _MODE_FILE) << 16
            zf.writestr(info, data)
    return buffer.getvalue(), entries, rev_label


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _ledger_text(zip_name, data, entries, rev, tree):
    lines = [
        "# plan/DIST-sha256-M6.txt — 发布物 sha256 台账（由 tools/make_release.py 生成）",
        "# 打包面 = git 跟踪面；配方 = ZIP_STORED + 路径排序 + 固定 date_time + 固定外部属性",
        "# 复算：py -X utf8 tools/make_release.py --verify <zip> --rev v0.1.0",
        "zip_name: %s" % zip_name,
        "sha256: %s" % _sha256(data),
        "bytes: %d" % len(data),
        "files: %d" % len(entries),
        "rev: %s" % rev,
        "tree: %s" % tree,
        "built_date: %04d-%02d-%02d" % FIXED_DATE_TIME[:3],
    ]
    return "\n".join(lines) + "\n"


def _zip_entries(data):
    listing = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            listing[info.filename] = zf.read(info.filename)
    return listing


def cmd_build(args):
    if not _is_git_tree():
        if args.rev:
            sys.stdout.write("ZIP_BUILD_ERROR: 非 git 仓库，无法使用 --rev\n")
            return 2
        data, entries, rev_label = build_zip_bytes(None)
        tree = "(none)"
    else:
        rev = args.rev or "HEAD"
        tree = _resolve_rev(rev)
        data, entries, rev_label = build_zip_bytes(rev)
    out_path = os.path.abspath(args.out)
    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(out_path, "wb") as handle:
        handle.write(data)
    zip_name = os.path.basename(out_path)
    sys.stdout.write("ZIP_BUILD_OK\n")
    sys.stdout.write("zip: %s\n" % zip_name)
    sys.stdout.write("files: %d\n" % len(entries))
    sys.stdout.write("bytes: %d\n" % len(data))
    sys.stdout.write("sha256: %s\n" % _sha256(data))
    sys.stdout.write("rev: %s\n" % rev_label)
    if args.ledger:
        ledger_path = os.path.abspath(args.ledger)
        ledger_parent = os.path.dirname(ledger_path)
        if ledger_parent and not os.path.isdir(ledger_parent):
            os.makedirs(ledger_parent)
        with open(ledger_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_ledger_text(zip_name, data, entries, rev_label, tree))
        sys.stdout.write("ledger: %s\n" % os.path.basename(ledger_path))
    return 0


def cmd_verify(args):
    if not _is_git_tree():
        sys.stdout.write("ZIP_VERIFY_ERROR: 非 git 仓库，无法按 rev 复算\n")
        return 2
    rev = args.rev or "HEAD"
    with open(args.verify, "rb") as handle:
        actual = handle.read()
    expected, entries, rev_label = build_zip_bytes(rev)
    if actual == expected:
        sys.stdout.write("ZIP_VERIFY_OK\n")
        sys.stdout.write("zip: %s\n" % os.path.basename(args.verify))
        sys.stdout.write("files: %d\n" % len(entries))
        sys.stdout.write("bytes: %d\n" % len(actual))
        sys.stdout.write("sha256: %s\n" % _sha256(actual))
        sys.stdout.write("rev: %s\n" % rev_label)
        return 0
    sys.stdout.write("ZIP_VERIFY_FAILED\n")
    sys.stdout.write("actual_sha256: %s\n" % _sha256(actual))
    sys.stdout.write("expect_sha256: %s\n" % _sha256(expected))
    try:
        actual_entries = _zip_entries(actual)
    except zipfile.BadZipFile:
        sys.stdout.write("actual: 不是合法 zip\n")
        return 1
    expect_entries = _zip_entries(expected)
    missing = sorted(set(expect_entries) - set(actual_entries))
    extra = sorted(set(actual_entries) - set(expect_entries))
    changed = sorted(name for name in expect_entries
                     if name in actual_entries and expect_entries[name] != actual_entries[name])
    for label, names in (("missing", missing), ("extra", extra), ("changed", changed)):
        for name in names[:20]:
            sys.stdout.write("  %s: %s\n" % (label, name))
    return 1


def main(argv=None):
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="发布物打包器（确定性源码 zip + sha256）")
    parser.add_argument("--rev", help="tree-ish（发布时传 tag；缺省 HEAD）")
    parser.add_argument("--out", help="构建模式：zip 输出路径")
    parser.add_argument("--ledger", help="构建模式：同时写入 sha256 台账路径")
    parser.add_argument("--verify", help="校验模式：比对给定 zip 与 --rev 的重建结果")
    args = parser.parse_args(argv)
    if args.verify and args.out:
        parser.error("--verify 与 --out 不能同时使用")
    try:
        if args.verify:
            return cmd_verify(args)
        if args.out:
            return cmd_build(args)
    except RuntimeError as exc:
        sys.stdout.write("ZIP_ERROR: %s\n" % exc)
        return 2
    parser.error("需要 --out（构建）或 --verify（校验）")
    return 2


if __name__ == "__main__":
    sys.exit(main())
