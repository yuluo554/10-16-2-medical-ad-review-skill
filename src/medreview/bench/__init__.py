"""基准套件（**包内**——三种调用通路都可达：``python -m`` / 裸 ``medreview`` / 冻结态）。

分三个文件：
  ``cases.py``  —— 对账语义的**单一实现源**（真值库测试与基准共用同一函数）
  ``runner.py`` —— B1–B4 一条命令跑全，退出码 0/1/2
  ``ledger.py`` —— 冻结台账校验（``check_frozen_ledger``，与生成器 ``--check`` 同源）
"""

from .runner import main, run_benchmarks  # noqa: F401
