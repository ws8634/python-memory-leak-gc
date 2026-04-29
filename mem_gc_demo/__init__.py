"""
Python 内存管理与GC演示包

本包用于演示：
1. 引用计数与循环引用
2. 分代GC机制
3. 容器导致的内存泄漏
4. 线上排查思路

使用方式: python -m mem_gc_demo <子命令>
查看子命令: python -m mem_gc_demo
"""

__version__ = "1.0.0"
