"""数据路径解析与冻结态定位。

纪律：路径优先级显式分支并配测试锁死（改优先级属"动了会打挂测试"的口径变更）。
本项目不做冻结 exe，故无 ``sys._MEIPASS`` 分支；保留"显式入参 > 环境变量 >
包内随包数据 > 仓库开发态"四级，供后续形态扩展。
"""

from __future__ import annotations

import os

# 环境变量名（测试与演示可显式指向临时目录；**临时目录必须显式传**，
# 防"缺省值有副作用"时扫进真实数据——见 plan/02 §六）
ENV_DATA_DIR = "MEDREVIEW_DATA_DIR"

# 本模块所在包目录：src/medreview/
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
# 仓库根：src/medreview/ → src/ → 仓库根
_REPO_ROOT = os.path.dirname(os.path.dirname(_PKG_DIR))


def package_references_dir():
    """包内随包规则包目录（安装面的一部分，pyproject package-data 已声明）。"""
    return os.path.join(_PKG_DIR, "references")


def package_fixtures_dir():
    """包内随包真值库目录。"""
    return os.path.join(_PKG_DIR, "fixtures")


def repo_root():
    """开发态仓库根（**不是**安装态的可靠定位，仅用于开发工具）。"""
    return _REPO_ROOT


def data_dir(explicit=None):
    """解析数据目录：显式入参 > 环境变量 > 包内随包目录。"""
    if explicit:
        return os.path.abspath(explicit)
    env = os.environ.get(ENV_DATA_DIR)
    if env:
        return os.path.abspath(env)
    return package_references_dir()


def ruleset_path(explicit=None):
    return os.path.join(data_dir(explicit), "ruleset.json")


def manifest_path(explicit=None):
    return os.path.join(data_dir(explicit), "manifest.json")


def clauses_path(explicit=None):
    return os.path.join(data_dir(explicit), "clauses.json")
