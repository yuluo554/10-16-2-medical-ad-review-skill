"""安装面/指令面/测试面 一致性守门（**五面对账**，一个文件锁死）。

五面（与 skill 的"安装面四面 + 包布局"同源）：

  面①  README 里出现的 CLI 子命令与旗标 → 必须真在 ``build_parser()`` 里注册
        （**逐行关联**：旗标要挂在对的子命令上，防"旗标写在错的命令行上"）
  面②  ``build_parser()`` 注册的子命令 → README 必须提及（反向覆盖）
  面③  ``tests/`` 全部 import（AST 从严收集，**含函数体内 import**）→
        落点四分法：stdlib 冻结名单 / dev extra / 本包 / tools 注入模块
  面④  README 的 extras 行 ↔ pyproject 的 extras 声明（双向）
  面⑤  ``packages.find`` 的 include → 真实包布局（解析到的目录必须真存在）

纪律（skill 定稿，踩过的坑）：
  - stdlib 判定**用冻结名单制**，不用 ``sys.stdlib_module_names``
    （3.10+ 才有；3.8 上取到空集 → 每个标准库都判成第三方 → 全量假红）。
  - 分发名 ↔ import 名走**别名表**（Pillow→PIL、pyyaml→yaml），直接比较会造假红。
  - 文本抽取类守门必须自证"扫描面非空"，且首轮变异验证要专门检查
    "探针有没有把目标文本切坏"（抽取到空集也是红不了的原因之一）。
"""

from __future__ import annotations

import ast
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from medreview import cli  # noqa: E402

# ---- 冻结名单：Python 3.8 标准库顶层模块（**不用 sys.stdlib_module_names**） ----
STDLIB_3_8 = frozenset("""
abc aifc argparse array ast asynchat asyncio asyncore atexit audioop base64 bdb
binascii binhex bisect builtins bz2 calendar cgi cgitb chunk cmath cmd code
codecs codeop collections colorsys compileall concurrent configparser contextlib
contextvars copy copyreg crypt csv ctypes curses dataclasses datetime dbm decimal
difflib dis distutils doctest dummy_threading email encodings ensurepip enum
errno faulthandler fcntl filecmp fileinput fnmatch formatter fractions ftplib
functools gc getopt getpass gettext glob graphlib grp gzip hashlib heapq hmac
html http idlelib imaplib imghdr imp importlib inspect io ipaddress itertools
json keyword lib2to3 linecache locale logging lzma mailbox mailcap marshal math
mimetypes mmap modulefinder msilib msvcrt multiprocessing netrc nis nntplib nt
numbers operator optparse os ossaudiodev parser pathlib pdb pickle pickletools
pipes pkgutil platform plistlib poplib posix posixpath pprint profile pstats
pty pwd py_compile pyclbr pydoc queue quopri random re readline reprlib
resource rlcompleter runpy sched secrets select selectors shelve shlex shutil
signal site smtplib sndhdr socket socketserver spwd sqlite3 sre_compile
sre_constants sre_parse ssl stat statistics string stringprep struct subprocess
sunau symbol symtable sys sysconfig syslog tabnanny tarfile telnetlib tempfile
termios test textwrap threading time timeit tkinter token tokenize trace
traceback tracemalloc tty turtle turtledemo types typing unicodedata unittest
urllib uu uuid venv warnings wave weakref webbrowser winreg winsound wsgiref
xdrlib xml xmlrpc zipapp zipfile zipimport zlib zoneinfo
__future__ _thread _dummy_thread _locale _collections_abc _sitebuiltins
""".split())

# 分发名 → import 名（别名表；直接比较会造假红）
DIST_TO_IMPORT = {
    "pytest": "pytest",
    "pyyaml": "yaml",
    "pillow": "PIL",
    "python-dateutil": "dateutil",
    "attrs": "attr",
    "beautifulsoup4": "bs4",
    "pyinstaller": "PyInstaller",
}

# 允许的"本包内部/工具注入"模块名（tests 里直接 import 的同目录模块）
LOCAL_MODULES = frozenset({"check_workflows"})

TOOLS_MODULES = frozenset({"gen_ruleset", "gen_cases", "make_snapshots", "audit_repo", "make_release"})


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# 面①/面②：README ↔ CLI
# --------------------------------------------------------------------------
def _readme_commands():
    """从 README 的代码块里抽出 CLI 调用（``medreview <sub> ...`` 形态）。

    返回 ``[(subcommand, [flags...])]``；无代码块调用则返回空列表。
    """
    text = read(os.path.join(ROOT, "README.md"))
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    calls = []
    for block in blocks:
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            match = re.search(r"\bmedreview\s+([a-z][a-z-]*)", line)
            if not match:
                continue
            sub = match.group(1)
            flags = re.findall(r"(?<!\w)(--[a-z][a-z0-9-]*)", line)
            calls.append((sub, flags))
    return calls


def _parser_commands():
    """反射 ``build_parser()``：``{subcommand: set(flags)}``。"""
    parser = cli.build_parser()
    out = {}
    for action in parser._actions:
        if hasattr(action, "choices") and action.choices and action.dest == "command":
            for name, sub in action.choices.items():
                flags = set()
                for sub_action in sub._actions:
                    flags.update(sub_action.option_strings)
                out[name] = flags
    return out


def test_face1_readme_flags_exist_in_parser():
    """README 提到的每个子命令与旗标都真在 parser 里（逐行关联到子命令）。"""
    calls = _readme_commands()
    assert calls, "README 没有任何 CLI 调用代码块——扫描面为空（假门）"
    registered = _parser_commands()
    for sub, flags in calls:
        assert sub in registered, "README 提到未注册的子命令：%s" % sub
        for flag in flags:
            assert flag in registered[sub], \
                "README 在 `%s` 命令行上用了未注册的旗标：%s" % (sub, flag)


def test_face2_all_parser_commands_are_documented():
    """反向：parser 注册的子命令必须在 README 出现（防"隐藏命令"）。"""
    registered = _parser_commands()
    text = read(os.path.join(ROOT, "README.md"))
    for sub in registered:
        assert re.search(r"\bmedreview\s+%s\b" % re.escape(sub), text), \
            "子命令未在 README 中记录：%s" % sub


# --------------------------------------------------------------------------
# 面③：tests 全部 import → 落点四分法
# --------------------------------------------------------------------------
def _collect_imports(directory):
    """AST 从严收集（**含函数体内 import**）。"""
    found = set()
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(read(os.path.join(directory, name)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    found.add(node.module.split(".")[0])
    return found


def _declared_extras():
    """解析 pyproject 的 extras 声明（**结构位置**，不是"文件里出现过这串字"）。"""
    text = read(os.path.join(ROOT, "pyproject.toml"))
    extras = {}
    for match in re.finditer(r'^([a-z0-9-]+)\s*=\s*\[([^\]]*)\]', text, re.M):
        name = match.group(1)
        if name in ("dependencies", "requires"):
            continue
        dists = re.findall(r'"([A-Za-z0-9_.-]+)', match.group(2))
        extras[name] = {d.split(">")[0].split("=")[0].split("<")[0].strip().lower()
                        for d in dists}
    return extras


def test_face3_tests_imports_are_covered():
    """测试真 import 的每个第三方库都在 dev extra 里（测试面 = 安装面）。"""
    imports = _collect_imports(os.path.join(ROOT, "tests"))
    assert imports, "未收集到任何 import——扫描面为空（假门）"
    extras = _declared_extras()
    dev_dists = extras.get("dev", set())
    dev_imports = {DIST_TO_IMPORT.get(d, d) for d in dev_dists}

    unresolved = []
    for module in sorted(imports):
        if module in STDLIB_3_8:
            continue
        if module == "medreview" or module in LOCAL_MODULES or module in TOOLS_MODULES:
            continue
        if module in dev_imports:
            continue
        unresolved.append(module)
    assert not unresolved, "测试 import 的库不在 dev extra：%s" % unresolved


def test_face3_stdlib_freeze_list_is_usable():
    """自证：冻结名单在底线解释器上非空（防 3.10+ API 导致的空集假红）。"""
    assert len(STDLIB_3_8) > 100
    assert "os" in STDLIB_3_8 and "json" in STDLIB_3_8


# --------------------------------------------------------------------------
# 面④：README extras 行 ↔ pyproject extras
# --------------------------------------------------------------------------
def _readme_extras():
    text = read(os.path.join(ROOT, "README.md"))
    names = set()
    for match in re.finditer(r'pip install[^\n]*\[\s*([a-z0-9,\s-]+)\]', text):
        for name in match.group(1).split(","):
            name = name.strip()
            if name:
                names.add(name)
    return names


def test_face4_readme_extras_match_pyproject():
    """README 安装行里的每个 extra 都真在 pyproject 里声明（双向）。"""
    readme_extras = _readme_extras()
    assert readme_extras, "README 没有 extras 安装行——扫描面为空（假门）"
    declared = set(_declared_extras())
    missing = sorted(readme_extras - declared)
    assert not missing, "README 用了未声明的 extra：%s" % missing


# --------------------------------------------------------------------------
# 面⑤：包布局（packages.find 的 include → 真实目录）
# --------------------------------------------------------------------------
def test_face5_package_layout_resolves():
    """解析 package-dir 映射 → 断言解析到的目录**真存在**。

    判据落在解析结果上，不是"pyproject 里出现了某个词"
    （"看着对"的坏配置同样含那个词）。
    """
    text = read(os.path.join(ROOT, "pyproject.toml"))
    match = re.search(r'where\s*=\s*\[([^\]]*)\]', text)
    assert match, "pyproject 未声明 packages.find.where"
    roots = [p.strip().strip('"\'') for p in match.group(1).split(",") if p.strip()]
    assert roots, "packages.find.where 为空"

    found_packages = []
    for root in roots:
        base = os.path.join(ROOT, root)
        assert os.path.isdir(base), "packages.find.where 指向不存在的目录：%s" % root
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, "__init__.py")):
                found_packages.append(name)
    assert "medreview" in found_packages, \
        "本包未被 packages.find 收集到：%s" % found_packages

    # 包内随包数据必须真在位（否则安装态装配失败）
    refs = os.path.join(ROOT, "src", "medreview", "references")
    assert os.path.isfile(os.path.join(refs, "ruleset.json"))
    assert os.path.isfile(os.path.join(refs, "clauses.json"))
    assert os.path.isfile(os.path.join(refs, "manifest.json"))


def test_face5_bench_is_in_package():
    """基准套件在包内（三种调用通路都可达），**不在仓库顶层**（会被漏装）。"""
    assert os.path.isfile(os.path.join(SRC, "medreview", "bench", "__init__.py"))
    assert not os.path.isdir(os.path.join(ROOT, "benchmark")), \
        "顶层 benchmark/ 会被漏装（安装面第四面缺陷家族）"


# --------------------------------------------------------------------------
# README 引用的仓库路径必须真存在（具名路径门禁）
# --------------------------------------------------------------------------
def test_readme_named_paths_exist():
    text = read(os.path.join(ROOT, "README.md"))
    paths = set(re.findall(r"(?<![\w/])((?:src|tests|tools|data|plan|\.github)/[\w./-]+)", text))
    assert paths, "README 未引用任何仓库路径——扫描面为空（假门）"
    missing = sorted(p for p in paths if not os.path.exists(os.path.join(ROOT, p)))
    assert not missing, "README 引用了不存在的路径：%s" % missing


def test_readme_has_required_sections():
    text = read(os.path.join(ROOT, "README.md"))
    for section in ("安装", "快速开始", "免责", "隐私"):
        assert section in text, "README 缺必备节：%s" % section
