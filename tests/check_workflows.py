"""CI workflow 结构守门（**独立脚本，供 CI 的 workflow-lint job 调用**）。

防的是一类静默失效：workflow YAML 里"步骤名带冒号+空格且未加引号"会让整份
workflow 变成非法 YAML → GitHub **建 0 个 job**、run 0 秒失败，而 workflow 仍显示
`state: active`、字节看起来干净（实测过的坑）。本脚本把 YAML 解析 + 结构断言
做成可本机复跑的守门。

用法：py -3.12 -X utf8 tests/check_workflows.py
退出码：0 全部合法 / 2 发现问题（用法/配置错误语义）
"""

from __future__ import annotations

import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - dev extra 缺失时的显式降级
    sys.stderr.write("需要 pyyaml（dev extra）：py -m pip install -e \".[dev]\"\n")
    sys.exit(3)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(ROOT, ".github", "workflows")


def check_workflow(path):
    problems = []
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return ["YAML 解析失败：%s" % exc]

    if not isinstance(data, dict):
        return ["顶层不是映射（YAML 结构非法）"]

    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        problems.append("jobs 缺失或为空（GitHub 会建 0 个 job）")
        return problems

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            problems.append("job %s 不是映射" % job_id)
            continue
        if not job.get("runs-on"):
            problems.append("job %s 缺 runs-on" % job_id)
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            problems.append("job %s 缺 steps（或为空）" % job_id)
            continue
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                problems.append("job %s step %d 不是映射" % (job_id, index))
                continue
            if not (step.get("run") or step.get("uses")):
                problems.append("job %s step %d 既无 run 也无 uses" % (job_id, index))

    # 历史扫描类守门若存在，必须 fetch-depth: 0（浅克隆会静默空验）
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "checkout" in str(step.get("uses", "")):
                with_block = step.get("with") or {}
                depth = with_block.get("fetch-depth")
                if depth is not None and str(depth) != "0":
                    problems.append("job %s 的 checkout fetch-depth=%s（历史扫描会空验）"
                                    % (job_id, depth))
    return problems


def main():
    if not os.path.isdir(WORKFLOW_DIR):
        sys.stderr.write("workflow 目录不存在：%s\n" % WORKFLOW_DIR)
        return 2
    files = sorted(f for f in os.listdir(WORKFLOW_DIR) if f.endswith((".yml", ".yaml")))
    if not files:
        sys.stderr.write("workflow 目录为空\n")
        return 2

    failed = []
    for name in files:
        problems = check_workflow(os.path.join(WORKFLOW_DIR, name))
        if problems:
            failed.append(name)
            sys.stdout.write("FAIL %s\n" % name)
            for problem in problems:
                sys.stdout.write("  - %s\n" % problem)
        else:
            sys.stdout.write("PASS %s\n" % name)

    if failed:
        sys.stdout.write("WORKFLOW_LINT_FAILED\n")
        return 2
    sys.stdout.write("WORKFLOW_LINT_OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
