"""词面匹配原语（**唯一实现源**：规则核查与品类判定共用）。

本模块只放"一个中文词面在文本中的某次出现是否构成**有效命中**"的**语言层**
判据，自身不含任何政策词面（既定口径 K9）——词表一律由调用方从冻结规则包
传入。规则核查（``check``）与品类判定（``categorize``）共用本模块，
**不各写一份**：两份以上即口径漂移源（"同一份判定，在几个地方各写了一份？"）。

三条判据（任一不成立，该次出现不算命中）：

1. **否定辖域**：命中项之前的同一句读段内存在**真否定词** → 不算命中。
   为什么必须有：本领域法条**强制要求**写免责语，而免责语恰含被禁词面；
   把合规的免责声明报成违法，比漏报更坏（用户按提示改文案反而改错）。
2. **排除语境**：命中项落在某个**更大词形内部** → 不算命中。
   为什么必须有：裸词与中性词形碰撞（"某词 + 系"式形容用法、机构名/品类名里
   顺带含词），无法靠词表长度阈值解决。
3. **逐处扫描**：同一词面在文中**任一处**有效即算命中——某处被否定不影响别处。

否定词表、非否定词例外表、句读分隔符都是**结构性常量**（见 ``constants``）：
它们换任何一部中文法规都成立，不是本领域政策字面量。
"""

from __future__ import annotations

from . import constants


def is_negated(text, index):
    """下标处是否处于否定辖域内。

    判据（两条都要满足才算"被否定"）：
      ① **辖域不跨句读**：只看从上一个句读分隔符到命中项起点之间的片段；
      ② 该片段里存在一个**真否定词**——即不是 ``NON_NEGATION_WORDS`` 成员的
         那一个（「不」开头的非否定词修饰主语，不是否定谓语，见下表）。

    为什么不是"否定词必须紧贴"：法条强制要求的免责语形态常是
    「否定词 + 动词 + 被禁词面」（如「不能保证…」），中间隔着动词；
    紧贴判定会漏掉它们，而"片段内出现真否定词"能覆盖该形态，同时靠例外表
    挡住"否定词修饰别的主语"型漏报。
    """
    start = index
    while start > 0 and text[start - 1] not in constants.SEGMENT_DELIMITERS:
        start -= 1
    prefix = text[start:index]
    for marker in constants.NEGATION_MARKERS:
        pos = prefix.find(marker)
        while pos >= 0:
            tail = prefix[pos:]
            # 该出现位置若是某个"非否定词"的开头，不算否定
            if not any(tail.startswith(word) for word in constants.NON_NEGATION_WORDS):
                return True
            pos = prefix.find(marker, pos + 1)
    return False


def excluded_context(text, term, index, contexts):
    """命中项是否落在**排除语境**内（该处更大的词形把它"包住"了）。

    用途：同一词面在中性词形里出现时不算命中（裸词与其"XX 系"式中性词形碰撞）。
    判据是**位置包含**：命中项的出现区间落在某个排除语境的
    出现区间内即跳过。排除语境来自规则包（数据），不是代码里的特例。
    """
    for context in contexts or ():
        if not context or term not in context:
            continue
        start = 0
        while True:
            found = text.find(context, start)
            if found < 0:
                break
            if found <= index and index + len(term) <= found + len(context):
                return True
            start = found + 1
    return False


def term_is_live(text, term, contexts=None):
    """词面是否**存在且未被否定、也未落在排除语境里**。

    全部出现位置都被否定/被排除 → 视为未命中（"合规免责语"与"中性词形"两类
    误报的唯一拦截点）。
    """
    start = 0
    while True:
        index = text.find(term, start)
        if index < 0:
            return False
        if not is_negated(text, index) and not excluded_context(text, term, index,
                                                              contexts):
            return True
        start = index + 1


def any_of(text, terms, contexts=None):
    """命中任一（返回命中项列表，保持调用方给出的顺序；排除否定/排除语境）。"""
    return [t for t in terms if t and term_is_live(text, t, contexts)]


def all_of(text, terms, contexts=None):
    """全部命中才命中（返回命中项；未全中返回空）。"""
    if not terms:
        return []
    hits = [t for t in terms if t and term_is_live(text, t, contexts)]
    return hits if len(hits) == len(terms) else []


def none_of(text, terms, contexts=None):
    """必须一个都不出现（返回空列表表示"通过"）。"""
    return [t for t in terms if t and term_is_live(text, t, contexts)]
