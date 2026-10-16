"""输入标准化（模块 1）。

唯一 ID 由原文哈希确定性派生——**不用随机数、不用时钟**，保证"同输入同 id"，
这是报告可复现与基准可对账的前提。
"""

from __future__ import annotations

import hashlib
import os

from .errors import InputUnavailable
from .model import ContentItem

ID_LENGTH = 12


def content_id(text):
    """确定性内容 ID：原文 UTF-8 字节的 sha256 前 12 位十六进制。"""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:ID_LENGTH]


def read_proof_file(path):
    """读取证明材料并算出**可追溯摘要**（只记文件名 + sha256 + 字节数）。

    纪律：报告里**不落全路径**（本地目录结构不外泄，报告可对外传阅）；
    可追溯性由 sha256 承担——同一份材料永远同一摘要，可据以复核。
    本函数**只算摘要，不解析内容**：实质核验仍以原件为准（报告如实写明）。
    """
    if not os.path.isfile(path):
        raise InputUnavailable("证明材料文件不存在: %s" % path,
                               code="proof_file_missing")
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        raise InputUnavailable("证明材料读取失败: %s (%s)" % (path, exc),
                               code="proof_file_read")
    return {
        "name": os.path.basename(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def normalize_text(text, channel=None, subject=None, hint=None, proof=None,
                   source_path=None, scenario=None, proof_file=None):
    """把一段文案标准化成 ``ContentItem``。

    空/仅空白文案是**输入不可用**（退出码 2），不是"未命中"——"没内容可查"
    与"查了没问题"必须可区分。
    """
    if text is None:
        raise InputUnavailable("文案为空（未提供内容）", code="empty_text")
    if not text.strip():
        raise InputUnavailable("文案仅含空白字符", code="blank_text")
    return ContentItem(
        item_id=content_id(text),
        text=text,
        channel=channel,
        subject=subject,
        hint=hint,
        proof=proof,
        source_path=source_path,
        scenario=scenario,
        proof_file=proof_file,
    )


def read_text_file(path):
    """读取文案文件（UTF-8，坏编码 → 输入不可用而非崩）。"""
    if not os.path.isfile(path):
        raise InputUnavailable("文案文件不存在: %s" % path, code="text_file_missing")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise InputUnavailable("文案文件不是合法 UTF-8: %s (%s)" % (path, exc),
                               code="text_file_encoding")
    except OSError as exc:
        raise InputUnavailable("文案文件读取失败: %s (%s)" % (path, exc),
                               code="text_file_read")
