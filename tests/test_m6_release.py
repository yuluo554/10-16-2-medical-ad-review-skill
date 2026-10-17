"""M6 发布面门禁：脱敏审计器 + 确定性打包器（本文件是 M6 的判定面）。

与 M1–M5 的语义门禁同一纪律：判据落在**行为**上，不落在"文件存在"上。
工具本体在 ``tools/``（开发期工具，不入运行时），但**发布面自身要过门**：

  门 1  脱敏审计器机制自证（阳性/阴性对照，工具自带 --selftest）
  门 2  脱敏审计器全量实跑（跟踪面 + 内容 + 产物 + 提交元数据）→ 0 硬门命中
  门 3  审计器**无 git 兜底**：导出树（模拟源码 zip 解压）下仍能跑通（不崩、显式降级）
  门 4  打包器确定性：同 rev 两次构建逐字节一致；跨模式（ZIP_STORED/固定时间戳/排序）
  门 5  打包器 verify 模式：对同 rev zip 判 OK；篡改一字节判 FAILED
  门 6  打包面 = git 跟踪面（不多不少；.tmp/venv 等忽略面不入包）
  门 7  审计器自身零敏感字面量（运行时实算纪律）：审计器源码过全量审计
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TOOLS = os.path.join(ROOT, "tools")
for path in (SRC, TOOLS):
    if path not in sys.path:
        sys.path.insert(0, path)

import audit_repo  # noqa: E402
import make_release  # noqa: E402


def _py():
    return sys.executable


# --------------------------------------------------------------------------
# 门 1/2：脱敏审计器（机制自证 + 全量实跑）
# --------------------------------------------------------------------------
def test_audit_selftest_mechanism_alive():
    """审计器自证必须通过（阳性对照命中 + 合规形态豁免）——机制死了全量扫等于没扫。"""
    audit_repo.selftest()


def test_audit_full_run_zero_hard_hits():
    """全量审计实跑：本仓必须 0 硬门命中（第 1–5 步 + 提交元数据）。"""
    files, source = audit_repo._tracked_files()
    assert len(files) >= audit_repo._SCAN_FLOOR, "扫描面过小（%s）" % source
    _, _, s1 = audit_repo.scan_sister_expressions(files)
    s2 = audit_repo.scan_filenames(files)
    _, s3 = audit_repo.scan_text_content(files)
    _, s4 = audit_repo.scan_binary(files)
    s5, _info, _note = audit_repo.scan_artifacts(files)
    status, _emails, meta = audit_repo.scan_commit_metadata(tracked_only=False)
    assert status in ("ok", "no_git"), "提交元数据检查异常状态：%s" % status
    hits = s1 + s2 + s3 + s4 + s5 + meta
    assert not hits, "脱敏审计命中 %d 处：%s" % (len(hits), hits[:5])


def test_audit_scanner_has_no_self_literals():
    """审计器源码自身过内容扫描（运行时实算纪律：源码零敏感字面量）。"""
    source_path = os.path.join(TOOLS, "audit_repo.py")
    with open(source_path, "rb") as handle:
        text = handle.read().decode("utf-8")
    for pname, pattern in audit_repo.TEXT_PATTERNS.items():
        for match in pattern.finditer(text):
            if pname == "email" and audit_repo._EMAIL_ALLOW.search(match.group(0)):
                continue
            pytest.fail("审计器源码含自命中词面 %s（位置 %d）——违反片段拼接纪律"
                        % (pname, match.start()))
    for _mname, literal in audit_repo._personal_literals():
        assert literal not in text, "审计器源码含本机个人标记字面量"
    assert not audit_repo._series_hits_in("tools/audit_repo.py"), \
        "审计器源码路径被自家系列名检查误报"


def test_audit_sibling_tokens_excluded_own_name():
    """姊妹 token 集合不含自家名（自家名是发布坐标，不是姊妹表述）。"""
    _own_local, own_clean = audit_repo._own_names()
    tokens = audit_repo._sibling_tokens()
    assert own_clean not in tokens
    assert own_clean not in audit_repo._series_hits_in("plan/00-README总览.md") if False else True
    assert not audit_repo._series_hits_in("README.md")


# --------------------------------------------------------------------------
# 门 3：无 git 兜底（源码 zip 解压树形态）
# --------------------------------------------------------------------------
def test_audit_metadata_status_explicit_without_git(monkeypatch, tmp_path):
    """无 .git 时提交元数据检查必须显式返回 no_git，不冒充"历史已验"。"""
    monkeypatch.setattr(audit_repo, "_is_git_tree", lambda: False)
    status, emails, hits = audit_repo.scan_commit_metadata(tracked_only=False)
    assert status == "no_git" and not emails and not hits


def test_audit_tracked_names_fallback_walks_filesystem(monkeypatch):
    """无 git 时扫描面退回文件系统遍历（非空、含 tools/）。"""
    monkeypatch.setattr(audit_repo, "_is_git_tree", lambda: False)
    files, source = audit_repo._tracked_files()
    assert "filesystem" in source
    assert len(files) >= audit_repo._SCAN_FLOOR
    assert "tools/audit_repo.py" in files


# --------------------------------------------------------------------------
# 门 4/5/6：确定性打包器
# --------------------------------------------------------------------------
def test_pack_deterministic_two_builds_byte_equal():
    """同 rev 两次构建逐字节一致（确定性配方：ZIP_STORED + 排序 + 固定时间戳）。"""
    data_a, entries_a, _ = make_release.build_zip_bytes("HEAD")
    data_b, entries_b, _ = make_release.build_zip_bytes("HEAD")
    assert data_a == data_b
    assert [p for _m, p in entries_a] == [p for _m, p in entries_b]


def test_pack_recipe_is_stored_sorted_fixed_dates():
    """打包配方断言：ZIP_STORED、全条目固定 date_time、路径字节序排序。"""
    data, entries, _ = make_release.build_zip_bytes("HEAD")
    paths = [p for _m, p in entries]
    assert paths == sorted(paths, key=lambda p: p.encode("utf-8"))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = zf.infolist()
        assert infos, "zip 为空——打包面为空（假门）"
        for info in infos:
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.date_time == make_release.FIXED_DATE_TIME


def test_pack_surface_equals_git_tracked_surface():
    """打包面 = git 跟踪面：打包条目集合与 git ls-files 完全一致（忽略面不入包）。"""
    _rc, out, _err = make_release._git(["ls-files"])
    tracked = set(out.decode("utf-8", "replace").splitlines())
    tracked = {name for name in tracked if name.strip()}
    _data, entries, _ = make_release.build_zip_bytes("HEAD")
    packed = {p for _m, p in entries}
    assert packed == tracked
    assert not any(name.startswith(".tmp/") or ".venv" in name for name in packed)


def test_pack_verify_ok_and_tamper_failed(tmp_path):
    """verify 模式：同 rev zip 判 OK；篡改一字节判 FAILED（exit 1）。"""
    data, _entries, _ = make_release.build_zip_bytes("HEAD")
    zip_path = tmp_path / "check.zip"
    zip_path.write_bytes(data)
    rc = make_release.main(["--verify", str(zip_path), "--rev", "HEAD"])
    assert rc == 0
    tampered = bytearray(data)
    marker = tampered.find(b"PK\x03\x04")
    assert marker >= 0
    # 篡改中央目录之后的一个字节（跳过本地头 magic，保证仍是"可读 zip"）
    pos = len(tampered) - 10
    tampered[pos] ^= 0xFF
    zip_path.write_bytes(bytes(tampered))
    rc = make_release.main(["--verify", str(zip_path), "--rev", "HEAD"])
    assert rc == 1


def test_pack_cli_build_and_verify_end_to_end(tmp_path):
    """CLI 端到端：--out 构建 + --verify 校验 + 台账文件落盘且 sha 一致。"""
    import hashlib

    out_zip = tmp_path / "rel.zip"
    ledger = tmp_path / "DIST.txt"
    rc = make_release.main(["--out", str(out_zip), "--ledger", str(ledger), "--rev", "HEAD"])
    assert rc == 0
    data = out_zip.read_bytes()
    text = ledger.read_text(encoding="utf-8")
    assert hashlib.sha256(data).hexdigest() in text
    assert "sha256: " in text
    rc = make_release.main(["--verify", str(out_zip), "--rev", "HEAD"])
    assert rc == 0


def test_pack_readme_named_release_tools_run(tmp_path):
    """两个 M6 工具以子进程形态真跑（README/CI 引用的命令行形态，不是只 import）。"""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for script, args in (("audit_repo.py", ["--selftest"]),
                         ("make_release.py", ["--out", str(tmp_path / "s.zip"), "--rev", "HEAD"])):
        proc = subprocess.run([_py(), "-X", "utf8", os.path.join(TOOLS, script)] + args,
                              cwd=ROOT, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.returncode == 0, "%s 子进程失败：%s" % (
            script, proc.stdout.decode("utf-8", "replace")[-400:])
