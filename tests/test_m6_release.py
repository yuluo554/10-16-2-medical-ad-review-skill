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
    # ok=完整历史；shallow=浅克隆检出形态（工具显式 INCOMPLETE，不冒充"历史已验"；
    # CI checkout 为 fetch-depth: 0，走 ok。no_git=导出树。
    assert status in ("ok", "no_git", "shallow"), "提交元数据检查异常状态：%s" % status
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
    """姊妹 token 集合与系列名检查都不含自家名（自家名是发布坐标，不是姊妹表述）。

    自家名**数据驱动**（README 自指 URL），与检出目录名无关——
    变异：把仓库 clone/改名到任意目录，自家 badge 仍不得误报。
    """
    _own_local, own_clean = audit_repo._own_names()
    assert own_clean, "自家名推导为空（README 自指 URL 缺失？）"
    tokens = audit_repo._sibling_tokens()
    assert own_clean not in tokens
    assert not audit_repo._series_hits_in("https://github.com/yuluo554/%s/releases" % own_clean)
    # 自家名的带前缀变体同样允许（本地目录名形态）
    own_local, _ = audit_repo._own_names()
    assert not audit_repo._series_hits_in(own_local)


# --------------------------------------------------------------------------
# 门 2.5：**仓库主人名**不是姊妹目录名（2026-10-23 实测缺陷的防回退）
#
# 缺陷形态：工作区里 profile 仓的目录叫 `<系列前缀>-<owner>`，`_sibling_tokens()` 去前缀后
# 得到的就是 owner 登录名，于是本仓每一处 owner 出现（README badge / LICENSE 版权行 /
# pyproject authors）都被判成「姊妹目录名」。它只在开发机工作区成立——CI 与干净 clone
# 的父目录没有姊妹目录，token 集为空，所以 CI 全绿发现不了。
# 修复前实测：本仓仓库态 10 处硬门命中，同一份 zip 解压到中立目录 0 处。
# --------------------------------------------------------------------------
def test_audit_owner_login_is_not_a_sibling_token():
    """owner 登录名必须从姊妹 token 集里排除（它出现在每一行 badge 与 LICENSE 里）。"""
    owner = audit_repo._own_owner()
    assert owner, "owner 推导为空（README 自指 URL 缺失？）"
    tokens = audit_repo._sibling_tokens()
    assert owner not in tokens, "owner 登录名被当成姊妹目录名：%r" % tokens[:5]
    # 阴性对照：owner 与仓库名拼接（badge URL 形态）不得判命中
    own_local, own_clean = audit_repo._own_names()
    assert not audit_repo._sibling_hits_in(
        "https://github.com/%s/%s/releases" % (owner, own_clean), tokens)


def test_audit_foreign_sibling_still_caught():
    """**阳性对照**：排除 owner 不能把真姊妹名一起放过。

    只喂三个条目——自家目录 + owner profile 目录 + 一个别人的项目名：
    前两个必须被排除，第三个必须仍进 token 集并能命中。

    ⚠️ 那个"别人的项目名"一律在**运行期**拼出：写成字面量会让本文件自己命中
    step1（审计器把"测试里为验证门禁而写的样例"当成真姊妹表述）。
    """
    _own_local, own_clean = audit_repo._own_names()
    owner = audit_repo._own_owner()
    foreign = "10" + "-04-" + "food-label" + "-compliance-checker"
    entries = [own_clean, "10-18-" + owner, foreign]
    tokens = audit_repo._sibling_tokens_from(entries)
    assert owner not in tokens
    assert own_clean not in tokens
    assert foreign in tokens
    assert "food-label" + "-compliance-checker" in tokens
    assert audit_repo._sibling_hits_in("see " + foreign, tokens)


def test_audit_sibling_tokens_can_be_empty_on_a_neutral_parent():
    """纯函数在"父目录里没有姊妹"时必须返回空集（CI / 干净 clone 形态）。"""
    assert audit_repo._sibling_tokens_from([]) == []
    assert audit_repo._sibling_tokens_from([".git", "README.md"]) == []


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
    """git 树内：打包面 = git 跟踪面（不多不少；忽略面不入包）。

    导出树（无 .git）：打包面 = 文件系统遍历面——断言非空、含关键路径、
    排除 venv/缓存（"下载件解包后打包面仍成立"的发布物本体形态）。
    """
    if make_release._is_git_tree():
        _rc, out, _err = make_release._git(["ls-files"])
        tracked = set(out.decode("utf-8", "replace").splitlines())
        tracked = {name for name in tracked if name.strip()}
    else:
        tracked = None
    _data, entries, rev_label = make_release.build_zip_bytes(
        "HEAD" if tracked is not None else None)
    packed = {p for _m, p in entries}
    if tracked is not None:
        assert packed == tracked
    else:
        assert len(packed) >= make_release._SCAN_FLOOR if hasattr(
            make_release, "_SCAN_FLOOR") else len(packed) >= 40
        assert "tools/make_release.py" in packed and "README.md" in packed
        assert "filesystem" in rev_label
    assert not any(name.startswith(".tmp/") or ".venv" in name for name in packed)


def test_pack_verify_ok_and_tamper_failed(tmp_path):
    """verify 模式：同 rev zip 判 OK；篡改一字节判 FAILED（exit 1）。

    **导出树守门**：源码 zip 解压树无 ``.git``——``--verify`` 按设计 exit 2
    （显式报"无法按 rev 复算"，不静默通过）。本测试在 git 树内才有重建比对语义。
    """
    data, _entries, _ = make_release.build_zip_bytes("HEAD")
    zip_path = tmp_path / "check.zip"
    zip_path.write_bytes(data)
    if not make_release._is_git_tree():
        rc = make_release.main(["--verify", str(zip_path), "--rev", "HEAD"])
        assert rc == 2, "导出树下 --verify 应显式 exit 2（不静默通过）"
        return
    rc = make_release.main(["--verify", str(zip_path), "--rev", "HEAD"])
    assert rc == 0
    tampered = bytearray(data)
    marker = tampered.find(b"PK\x03\x04")
    assert marker >= 0
    # 篡改文件尾部的一个字节（跳过本地头 magic，保证仍是"可读 zip"）
    pos = len(tampered) - 10
    tampered[pos] ^= 0xFF
    zip_path.write_bytes(bytes(tampered))
    rc = make_release.main(["--verify", str(zip_path), "--rev", "HEAD"])
    assert rc == 1


def test_pack_cli_build_and_verify_end_to_end(tmp_path):
    """CLI 端到端：--out 构建 + --verify 校验 + 台账文件落盘且 sha 一致。

    导出树（无 .git）：--out 走文件系统遍历兜底仍可构建；--verify 步骤跳过。
    """
    import hashlib

    out_zip = tmp_path / "rel.zip"
    ledger = tmp_path / "DIST.txt"
    rc = make_release.main(["--out", str(out_zip), "--ledger", str(ledger),
                            "--rev", "HEAD" if make_release._is_git_tree() else None])
    assert rc == 0
    data = out_zip.read_bytes()
    text = ledger.read_text(encoding="utf-8")
    assert hashlib.sha256(data).hexdigest() in text
    assert "sha256: " in text
    if make_release._is_git_tree():
        rc = make_release.main(["--verify", str(out_zip), "--rev", "HEAD"])
        assert rc == 0


def test_pack_readme_named_release_tools_run(tmp_path):
    """两个 M6 工具以子进程形态真跑（README/CI 引用的命令行形态，不是只 import）。

    导出树（无 .git）：make_release 不传 --rev（走文件系统兜底）；
    输出 zip 落 tmp_path（**不落遍历树内**，否则二次打包会把产物扫进去）。
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out_zip = tmp_path / ("s.zip" if make_release._is_git_tree() else "s-fs.zip")
    release_args = [] if make_release._is_git_tree() else []
    if make_release._is_git_tree():
        release_args = ["--rev", "HEAD"]
    for script, args in (("audit_repo.py", ["--selftest"]),
                         ("make_release.py", ["--out", str(out_zip)] + release_args)):
        proc = subprocess.run([_py(), "-X", "utf8", os.path.join(TOOLS, script)] + args,
                              cwd=ROOT, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.returncode == 0, "%s 子进程失败：%s" % (
            script, proc.stdout.decode("utf-8", "replace")[-400:])
