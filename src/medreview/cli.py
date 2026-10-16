"""CLI 编排层（唯一命令入口）。

退出码契约（K2，锁进端到端测试）：
  0 = 完成且未命中（OK / NOT_ASSESSED）
  1 = **检出命中**（BLOCK / WARN）——"查出了问题"的既定语义，**不是故障**
  2 = 输入/用法错误
  3 = 规则包不可用

编码护栏：入口 ``_ensure_utf8_stdio()`` 按 ``stream.encoding`` 探针决定是否
reconfigure——本机中文控制台（cp936）保持不动，CI 的 cp1252 被救。
"""

from __future__ import annotations

import argparse
import io
import os
import sys

from . import constants, normalize, report as report_mod, serialize
from .errors import MedReviewError
from .paths import package_references_dir

PROG = "medreview"


def _ensure_utf8_stdio():
    """把 stdout/stderr 在需要时切到 UTF-8（探针式，不盲改）。

    纪律：本机一律用 ``py -X utf8`` 跑命令，但**代码里的非 ASCII 输出缺口会被
    它整体掩盖**——CI 管道是 cp1252 时同样代码会崩 ``UnicodeEncodeError``。
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding in ("utf8", "utf8mb4", "cp65001"):
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, io.UnsupportedOperation):
            pass


def build_parser():
    """构造参数解析器（README 契约的反射对象，供门禁测试逐行关联）。"""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="医疗/医美/药品/器械/保健食品广告合规预审体检（纯本地、确定性规则引擎）",
    )
    parser.add_argument("--version", action="store_true", help="打印版本并退出")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="审查单条文案")
    p_check.add_argument("--text", help="待审查文案（与 --text-file 二选一）")
    p_check.add_argument("--text-file", dest="text_file", help="待审查文案文件（UTF-8）")
    p_check.add_argument("--channel", help="发布渠道（元信息，不参与判定）")
    p_check.add_argument("--subject", help="主体类型（元信息）")
    p_check.add_argument("--hint", help="语境提示（只进报告 advisory，不改结论）")
    p_check.add_argument("--proof", help="广告审查证明：yes / no / 未提供")
    p_check.add_argument("--scenario", choices=("prepublication", "published"),
                         default="prepublication",
                         help="审查情形：prepublication=发布前自查（默认）/ published=已发布")
    p_check.add_argument("--format", choices=("markdown", "json"), default="markdown",
                         help="输出格式（默认 markdown）")
    p_check.add_argument("--out", help="产物输出路径（缺省打印到 stdout）")

    p_scan = sub.add_parser("scan", help="批量审查（逐行/逐文件）")
    p_scan.add_argument("--dir", dest="scan_dir", help="待审查文案目录（*.txt）")
    p_scan.add_argument("--format", choices=("markdown", "json"), default="json")
    p_scan.add_argument("--out", help="产物输出路径")

    p_rules = sub.add_parser("rules", help="列出规则包条目与锚点（含未启用清单）")
    p_rules.add_argument("--format", choices=("markdown", "json"), default="markdown")

    p_bench = sub.add_parser("bench", help="跑内置基准套件")
    p_bench.add_argument("--only", help="只跑指定套件（未知名 → 退出码 2）")

    sub.add_parser("selftest", help="内建自检（门禁阳性对照 + 装配完整性）")

    return parser


def _read_text_arg(args):
    if args.text and args.text_file:
        raise MedReviewError("--text 与 --text-file 不能同时提供", code="usage_error")
    if args.text is not None:
        return args.text
    if args.text_file:
        return normalize.read_text_file(args.text_file)
    raise MedReviewError("必须提供 --text 或 --text-file", code="usage_error")


def cmd_check(args):
    from . import pipeline
    text = _read_text_arg(args)
    engine = pipeline.build_engine()
    rep = pipeline.check_text(engine, text, channel=args.channel, subject=args.subject,
                              hint=args.hint, proof=args.proof, scenario=args.scenario)
    if args.format == "json":
        payload = report_mod.render_json(rep)
        text_out = serialize.dumps_json(payload)
    else:
        text_out = report_mod.render_markdown(rep)
    if args.out:
        serialize.write_text_atomic(args.out, text_out)
    else:
        sys.stdout.write(text_out)
    return constants.EXIT_FINDING if rep.grade in constants.GRADES_WITH_FINDING else constants.EXIT_OK


def cmd_scan(args):
    from . import pipeline
    if not args.scan_dir:
        raise MedReviewError("scan 必须提供 --dir", code="usage_error")
    if not os.path.isdir(args.scan_dir):
        raise MedReviewError("目录不存在: %s" % args.scan_dir, code="input_unavailable")

    engine = pipeline.build_engine()
    items = []
    for name in sorted(os.listdir(args.scan_dir)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(args.scan_dir, name)
        text = normalize.read_text_file(path)
        items.append(normalize.normalize_text(text, source_path=path))

    if not items:
        # "根本没得查" ≠ "查了没问题"：不产出一份空报告（伪造的空报告会被当"跑过了"）
        raise MedReviewError("目录下没有可审查的 .txt 文案：%s（无输入源，不产出报告）"
                             % args.scan_dir, code="no_input_source")

    results = pipeline.scan_items(engine, items)
    payload = {"results": []}
    any_finding = False
    failed = 0
    for entry in results:
        if entry["ok"]:
            rep = entry["report"]
            payload["results"].append(rep.to_dict())
            if rep.grade in constants.GRADES_WITH_FINDING:
                any_finding = True
        else:
            failed += 1
            # 失败件单列，不静默吞掉；**不改变退出码**（"没判定"≠"判出违规"）
            payload["results"].append({"id": entry["id"], "kind": "failed",
                                       "error": entry["error"]})

    payload["summary"] = {
        "total": len(results),
        "failed": failed,
        "finding": any_finding,
    }
    text_out = serialize.dumps_json(payload) if args.format == "json" \
        else report_mod.render_markdown(results[0]["report"]) if results else "（无输入）\n"
    if args.out:
        serialize.write_text_atomic(args.out, text_out)
    else:
        sys.stdout.write(text_out)
    return constants.EXIT_FINDING if any_finding else constants.EXIT_OK


def cmd_rules(args):
    from . import pipeline
    engine = pipeline.build_engine(scope=constants.SCOPE_RULES)
    if args.format == "json":
        payload = {
            "ruleset_version": engine.ruleset_version,
            "basis_date": engine.basis_date,
            "total_rule_count": engine.total_rule_count,
            "enabled": [r.to_dict() for r in engine.rules],
            "not_enabled": engine.not_enabled,
        }
        sys.stdout.write(serialize.dumps_json(payload))
        return constants.EXIT_OK

    lines = ["# 规则包条目", ""]
    lines.append("- 规则包版本：%s" % (engine.ruleset_version or "未派生"))
    lines.append("- 基准日：%s" % (engine.basis_date or "未提供"))
    lines.append("- 生效条目：%d" % len(engine.rules))
    lines.append("- 未启用条目：%d" % len(engine.not_enabled))
    lines.append("")
    lines.append("## 生效规则")
    lines.append("")
    for rule in engine.rules:
        lines.append("- `%s` [%s] %s" % (rule.rule_id, rule.severity, rule.anchor))
        lines.append("  - 原文：%s" % rule.quote)
        lines.append("  - 适用品类：%s" % "、".join(rule.categories))
    lines.append("")
    lines.append("## 未启用清单（不参与判定）")
    lines.append("")
    if not engine.not_enabled:
        lines.append("（空）")
    for entry in engine.not_enabled:
        lines.append("- `%s`：%s" % (entry["rule_id"], entry["reason"]))
    sys.stdout.write("\n".join(lines).rstrip("\n") + "\n")
    return constants.EXIT_OK


def cmd_bench(args):
    # 基准套件在**包内**（src/medreview/bench）——三种调用通路都可达：
    # python -m medreview.cli / 裸 medreview / 冻结态。放仓库顶层会被漏装
    # （"安装面第四面"实测缺陷家族），故不采用顶层 benchmark/ 包。
    from .bench import runner
    return runner.main(["--only", args.only] if args.only else [])


def cmd_selftest(args):
    from . import selftest
    return selftest.run_selftest()


def main(argv=None):
    _ensure_utf8_stdio()
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse 的用法错误本身就是退出码 2 语义
        return constants.EXIT_INPUT if exc.code != 0 else constants.EXIT_OK

    if args.version:
        from . import pipeline
        try:
            engine = pipeline.build_engine(scope=constants.SCOPE_RULES)
            sys.stdout.write("medreview %s\n" % (engine.ruleset_version or "未派生"))
        except MedReviewError as exc:
            sys.stdout.write("medreview 版本不可用（%s）\n" % exc)
            return constants.EXIT_RULESET
        return constants.EXIT_OK

    if not args.command:
        parser.print_help()
        return constants.EXIT_OK

    handler = {
        "check": cmd_check,
        "scan": cmd_scan,
        "rules": cmd_rules,
        "bench": cmd_bench,
        "selftest": cmd_selftest,
    }.get(args.command)
    if handler is None:
        parser.print_help()
        return constants.EXIT_INPUT

    try:
        return handler(args)
    except MedReviewError as exc:
        # 领域异常继承 ValueError → CLI 抓得住；退出码按 code 分档
        code = getattr(exc, "code", "")
        if code in ("ruleset_missing", "ruleset_bad_json", "anchor_unresolved",
                    "config_missing", "bad_scope"):
            if code == "config_missing":
                sys.stderr.write("[配置错误] %s\n" % exc.message)
                return constants.EXIT_INPUT
            sys.stderr.write("[规则包不可用] %s\n" % exc.message)
            return constants.EXIT_RULESET
        sys.stderr.write("[输入错误] %s\n" % exc.message)
        return constants.EXIT_INPUT
    except ValueError as exc:
        sys.stderr.write("[输入错误] %s\n" % exc)
        return constants.EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
