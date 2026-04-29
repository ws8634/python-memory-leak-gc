"""
Python 内存管理与GC演示 - 统一入口

使用方式:
    python -m mem_gc_demo              # 列出子命令
    python -m mem_gc_demo <子命令>     # 运行指定子命令

子命令:
    cyclic-refs    循环引用与弱引用对比
    gen-gc         分代GC演示 (带gc.collect开关)
    container-leak 容器持有导致的内存泄漏
    all            运行所有演示

退出码:
    0   成功
    1   空参数/无命令
    2   非法子命令
"""

import sys
import argparse
from typing import Dict, Callable


EXIT_SUCCESS = 0
EXIT_NO_COMMAND = 1
EXIT_INVALID_COMMAND = 2


def print_help(commands: Dict[str, str]):
    """打印帮助信息"""
    print("Python 内存管理与GC演示工具")
    print("=" * 50)
    print("\n使用方式:")
    print("  python -m mem_gc_demo              列出子命令")
    print("  python -m mem_gc_demo <子命令>     运行指定子命令")
    print("\n可用子命令:")
    for cmd, desc in commands.items():
        print(f"  {cmd:<15} {desc}")
    print("\n示例:")
    print("  python -m mem_gc_demo cyclic-refs")
    print("  python -m mem_gc_demo gen-gc")
    print("  python -m mem_gc_demo container-leak")
    print("  python -m mem_gc_demo all")


def cmd_cyclic_refs():
    """循环引用与弱引用对比"""
    from . import cyclic_ref
    cyclic_ref.run_cyclic_vs_weakref()
    cyclic_ref.run_explicit_disconnect()
    return EXIT_SUCCESS


def cmd_gen_gc():
    """分代GC演示"""
    from . import generational_gc
    generational_gc.run_comparison()
    return EXIT_SUCCESS


def cmd_container_leak():
    """容器持有导致的内存泄漏"""
    from . import container_leak
    container_leak.run_container_leak_demo()
    container_leak.run_weakref_vs_strongref_container()
    return EXIT_SUCCESS


def cmd_all():
    """运行所有演示"""
    print("=" * 70)
    print("运行所有演示")
    print("=" * 70)
    
    print("\n" + "#" * 70)
    print("# 第1部分: 循环引用与弱引用对比")
    print("#" * 70)
    result1 = cmd_cyclic_refs()
    
    print("\n" + "#" * 70)
    print("# 第2部分: 分代GC演示")
    print("#" * 70)
    result2 = cmd_gen_gc()
    
    print("\n" + "#" * 70)
    print("# 第3部分: 容器持有导致的内存泄漏")
    print("#" * 70)
    result3 = cmd_container_leak()
    
    print("\n" + "=" * 70)
    print("所有演示完成")
    print("=" * 70)
    
    return max(result1, result2, result3)


COMMANDS: Dict[str, Callable] = {
    "cyclic-refs": cmd_cyclic_refs,
    "gen-gc": cmd_gen_gc,
    "container-leak": cmd_container_leak,
    "all": cmd_all,
}

COMMAND_DESCRIPTIONS: Dict[str, str] = {
    "cyclic-refs": "循环引用与弱引用对比",
    "gen-gc": "分代GC演示 (带gc.collect开关)",
    "container-leak": "容器持有导致的内存泄漏",
    "all": "运行所有演示",
}


def main():
    """主入口函数"""
    if len(sys.argv) < 2:
        print_help(COMMAND_DESCRIPTIONS)
        print("\n错误: 未指定子命令", file=sys.stderr)
        sys.exit(EXIT_NO_COMMAND)
    
    cmd = sys.argv[1]
    
    if cmd in ("-h", "--help", "help"):
        print_help(COMMAND_DESCRIPTIONS)
        sys.exit(EXIT_SUCCESS)
    
    if cmd not in COMMANDS:
        print_help(COMMAND_DESCRIPTIONS)
        print(f"\n错误: 无效的子命令 '{cmd}'", file=sys.stderr)
        print(f"有效子命令: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(EXIT_INVALID_COMMAND)
    
    try:
        exit_code = COMMANDS[cmd]()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        print(f"\n执行错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
