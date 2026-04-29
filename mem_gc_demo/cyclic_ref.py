"""
引用计数与循环引用对比演示

演示两种场景：
1. 保留循环引用 - 对象间互相引用，引用计数永不为0
2. 使用弱引用/显式解除引用 - 打破循环，允许对象被回收

关键点：
- 循环引用会导致引用计数机制失效
- Python的分代GC可以检测到循环引用，但有延迟
- 使用弱引用(weakref)或手动断链可以避免循环引用问题
"""

import gc
import weakref
import sys


class TrackedObject:
    """可追踪的对象基类，用于观察创建和销毁"""
    _instances = {}
    _next_id = 0

    def __init__(self, name: str):
        self._id = TrackedObject._next_id
        TrackedObject._next_id += 1
        self.name = name
        TrackedObject._instances[self._id] = weakref.ref(self)

    def __del__(self):
        print(f"  [销毁] {self.__class__.__name__}({self._id}): {self.name}")
        if self._id in TrackedObject._instances:
            del TrackedObject._instances[self._id]

    @classmethod
    def count(cls) -> int:
        """返回当前存活的实例数量"""
        return sum(1 for ref in cls._instances.values() if ref() is not None)

    @classmethod
    def list_alive(cls) -> list:
        """返回当前存活的实例列表"""
        return [ref() for ref in cls._instances.values() if ref() is not None]


class NodeWithStrongRef(TrackedObject):
    """使用强引用的节点 - 会形成循环引用"""

    def __init__(self, name: str):
        super().__init__(name)
        self._other = None

    @property
    def other(self):
        return self._other

    @other.setter
    def other(self, value):
        self._other = value


class NodeWithWeakRef(TrackedObject):
    """使用弱引用的节点 - 不会形成循环引用"""

    def __init__(self, name: str):
        super().__init__(name)
        self._other_ref = None

    @property
    def other(self):
        if self._other_ref is not None:
            return self._other_ref()
        return None

    @other.setter
    def other(self, value):
        if value is not None:
            self._other_ref = weakref.ref(value)
        else:
            self._other_ref = None


def _print_refcount(obj, label: str):
    """打印引用计数（减去getrefcount本身的引用）"""
    count = sys.getrefcount(obj) - 1
    print(f"  引用计数({label}): {count}")


def run_cyclic_vs_weakref():
    """
    运行循环引用与弱引用的对比演示
    
    场景1: 强引用循环 - a <-> b 互相强引用
    场景2: 弱引用断开循环 - a -> b (强引用), b -> a (弱引用)
    """
    print("=" * 70)
    print("场景对比: 循环引用 vs 弱引用打破循环")
    print("=" * 70)

    gc.collect()
    gc.set_debug(gc.DEBUG_LEAK)
    TrackedObject._instances.clear()
    TrackedObject._next_id = 0

    print("\n[场景1] 强引用形成循环引用")
    print("-" * 50)
    
    a1 = NodeWithStrongRef("A1")
    b1 = NodeWithStrongRef("B1")
    
    print(f"\n创建节点后存活数: {TrackedObject.count()}")
    _print_refcount(a1, "a1")
    _print_refcount(b1, "b1")
    
    a1.other = b1
    b1.other = a1
    
    print(f"\n建立双向引用后存活数: {TrackedObject.count()}")
    _print_refcount(a1, "a1 (被b1引用后)")
    _print_refcount(b1, "b1 (被a1引用后)")
    
    print("\n删除局部变量 a1, b1...")
    del a1
    del b1
    
    print(f"删除局部变量后存活数: {TrackedObject.count()} (应仍为2，循环引用挂住)")
    
    print("\n调用 gc.collect()...")
    collected = gc.collect()
    print(f"GC回收的对象数: {collected}")
    print(f"GC后存活数: {TrackedObject.count()}")
    
    print("\n[场景2] 使用弱引用打破循环")
    print("-" * 50)
    
    TrackedObject._instances.clear()
    TrackedObject._next_id = 0
    
    a2 = NodeWithWeakRef("A2")
    b2 = NodeWithWeakRef("B2")
    
    print(f"\n创建节点后存活数: {TrackedObject.count()}")
    _print_refcount(a2, "a2")
    _print_refcount(b2, "b2")
    
    a2.other = b2
    b2.other = a2
    
    print(f"\n建立双向引用后存活数: {TrackedObject.count()}")
    _print_refcount(a2, "a2 (b2使用弱引用指向a2)")
    _print_refcount(b2, "b2 (a2使用弱引用指向b2)")
    
    print("\n删除局部变量 a2, b2...")
    del a2
    del b2
    
    print(f"删除局部变量后存活数: {TrackedObject.count()} (应为0，弱引用不增加计数)")
    
    print("\n调用 gc.collect()...")
    collected = gc.collect()
    print(f"GC回收的对象数: {collected}")
    print(f"GC后存活数: {TrackedObject.count()}")

    print("\n" + "=" * 70)
    print("对比结论:")
    print("=" * 70)
    print("1. 强引用循环: 即使删除局部变量，对象仍因循环引用挂住")
    print("   - 引用计数永不为0，必须依赖分代GC检测")
    print("2. 弱引用: 弱引用不增加引用计数，循环被打破")
    print("   - 删除局部变量后，对象可立即被回收")
    
    gc.set_debug(0)
    gc.collect()


def run_explicit_disconnect():
    """
    演示显式解除引用打破循环
    
    场景: 创建循环引用后，手动断链
    """
    print("\n" + "=" * 70)
    print("显式解除引用演示")
    print("=" * 70)

    gc.collect()
    TrackedObject._instances.clear()
    TrackedObject._next_id = 0

    print("\n[步骤1] 创建强引用循环")
    a = NodeWithStrongRef("A")
    b = NodeWithStrongRef("B")
    a.other = b
    b.other = a
    
    print(f"创建循环后存活数: {TrackedObject.count()}")
    
    print("\n[步骤2] 删除局部变量（循环引用仍存在）")
    ref_a = weakref.ref(a)
    ref_b = weakref.ref(b)
    del a
    del b
    
    print(f"删除局部变量后存活数: {TrackedObject.count()}")
    print(f"  ref_a() is None: {ref_a() is None}")
    print(f"  ref_b() is None: {ref_b() is None}")
    
    print("\n[步骤3] GC回收循环引用")
    collected = gc.collect()
    print(f"GC回收的对象数: {collected}")
    print(f"GC后存活数: {TrackedObject.count()}")
    print(f"  ref_a() is None: {ref_a() is None}")
    print(f"  ref_b() is None: {ref_b() is None}")

    print("\n" + "-" * 50)
    print("对比: 先手动断链再删除")
    print("-" * 50)

    TrackedObject._instances.clear()
    TrackedObject._next_id = 0

    a2 = NodeWithStrongRef("A2")
    b2 = NodeWithStrongRef("B2")
    a2.other = b2
    b2.other = a2
    
    print(f"\n创建循环后存活数: {TrackedObject.count()}")
    
    print("\n手动断链: a2.other = None, b2.other = None")
    a2.other = None
    b2.other = None
    
    print(f"断链后存活数: {TrackedObject.count()}")
    
    ref_a2 = weakref.ref(a2)
    ref_b2 = weakref.ref(b2)
    
    print("\n删除局部变量...")
    del a2
    del b2
    
    print(f"删除后存活数: {TrackedObject.count()} (立即回收)")
    print(f"  ref_a2() is None: {ref_a2() is None}")
    print(f"  ref_b2() is None: {ref_b2() is None}")

    gc.collect()


if __name__ == "__main__":
    run_cyclic_vs_weakref()
    run_explicit_disconnect()
