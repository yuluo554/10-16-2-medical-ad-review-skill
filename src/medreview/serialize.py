"""唯一写盘点（确定性序列化参数冻结）。

既定口径 K5：全项目所有产物写盘一律经本模块的 ``write_atomic``——
"换一个子命令，写盘形态会变吗？"会变 = 迟早出现"一个产物带 BOM、另一个不带"
"一个 sort_keys、另一个不排"的漂移。

序列化参数（冻结契约，改动即打挂全部字节一致性守门）：
  - ``json.dumps(sort_keys=True, ensure_ascii=False, indent=2)``
    ``ensure_ascii=False`` 是中文项目必选项：默认 True 会把中文转 \\uXXXX，
    diff 不可读且与"人读产物"定位矛盾。
  - 行尾固定 LF，结尾固定换行。
  - 原子写：写临时文件再 ``os.replace``，防中断留下半个产物。
"""

from __future__ import annotations

import json
import os
import tempfile

LF = "\n"


def dumps_json(payload):
    """确定性 JSON 文本（排序键 + 非 ASCII 原样 + 缩进 2 + LF + 结尾换行）。"""
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    if not text.endswith(LF):
        text += LF
    return text.replace("\r\n", LF)


def write_text_atomic(path, text):
    """原子写文本；**字节形态由本函数单点决定**（LF、无 BOM、结尾换行）。"""
    path = os.fspath(path)
    if not text.endswith(LF):
        text += LF
    text = text.replace("\r\n", LF)
    data = text.encode("utf-8")

    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(directory):
        raise OSError("输出目录不存在: %s" % directory)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path, payload):
    """确定性 JSON 落盘（经 ``dumps_json`` + ``write_text_atomic`` 单点）。"""
    write_text_atomic(path, dumps_json(payload))
    return os.fspath(path)
