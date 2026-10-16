"""官方全文快照抓取器（**开发期一次性工具，不在测试/CI 路径上**）。

用法：
    py -3.12 -X utf8 tools/make_snapshots.py

产出：``data/knowledge/raw/<source>.txt`` —— 剥标签后的正文文本快照。

三条纪律：
1. **快照必须入仓**（生成器消费的是入仓快照，不是网络）——CI 离线可跑；
2. **字节形态固定**：LF 行尾、UTF-8 无 BOM、无时间戳（否则 sha256 台账跨平台失配）；
3. 本脚本**不写入任何时间戳/抓取元信息**（抓取日记录在 ``data/ledger.csv`` 与文档里）。
"""

from __future__ import annotations

import html
import io
import os
import re
import sys
import urllib.request

# 抓取目标：来源 ID → 官方 URL（URL 属"数据来源登记"，由本工具集中持有）
SOURCES = [
    ("advertising_law",
     "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/"
     "art_5474cf75173c45d6a0379730fb4e8d97.html"),
    ("internet_ad_measures",
     "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/"
     "art_d93a579afd45413e8576e4623fab348f.html"),
    ("medical_ad_measures",
     "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ggjgs/art/2023/"
     "art_6584dc1c94c2408db7c73f0b5e3d225a.html"),
]

_RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "knowledge", "raw")


def strip_html(source):
    """剥标签为纯文本（块级标签转行，行内标签转空格，去空行）。"""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", source)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def fetch(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def write_snapshot(path, text):
    """LF + 无 BOM + 结尾换行（字节形态由本函数单点决定）。"""
    data = (text.rstrip("\n") + "\n").replace("\r\n", "\n").encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(data)


def main(argv=None):
    if not os.path.isdir(_RAW_DIR):
        os.makedirs(_RAW_DIR)
    for source_id, url in SOURCES:
        page = fetch(url)
        text = strip_html(page)
        path = os.path.join(_RAW_DIR, source_id + ".txt")
        write_snapshot(path, text)
        chinese = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        sys.stdout.write("%s: bytes=%d chinese=%d\n"
                         % (source_id, len(text.encode("utf-8")), chinese))
    return 0


if __name__ == "__main__":
    sys.exit(main())
