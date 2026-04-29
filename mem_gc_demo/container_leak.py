"""
容器持有导致的内存泄漏模拟

常见场景：
1. 全局dict/列表只添加不删除
2. 回调/监听器列表只注册不注销
3. 缓存无淘汰策略（无界缓存）

这类泄漏的特点：
- 内存占用随时间只增不减
- 对象被长期引用，即使业务逻辑已不再需要
- GC无法回收，因为引用计数不为0

排查线索：
- tracemalloc 追踪峰值和分配位置
- objgraph 查看对象增长趋势
- gc.get_referrers 查找引用来源
"""

import gc
import tracemalloc
import weakref
import sys


class DataObject:
    """数据对象 - 模拟业务数据"""
    _id_counter = 0
    
    def __init__(self, name: str, size: int = 100):
        self.id = DataObject._id_counter
        DataObject._id_counter += 1
        self.name = name
        self.data = [f"{name}_{i}" for i in range(size)]


class CallbackObject:
    """回调对象 - 模拟事件监听器"""
    _id_counter = 0
    
    def __init__(self, name: str):
        self.id = CallbackObject._id_counter
        CallbackObject._id_counter += 1
        self.name = name
        self._called = False
    
    def __call__(self, *args, **kwargs):
        self._called = True
        return f"Callback {self.name} called"


_global_data_store = {}
_global_callback_list = []


def memory_probe(prefix: str = "") -> dict:
    """
    内存探针 - 记录当前内存状态
    
    返回包含以下信息的字典:
    - tracemalloc 当前内存
    - tracemalloc 峰值内存
    - 全局容器大小
    - GC各代计数
    """
    result = {}
    
    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        result["tracemalloc_current_kb"] = current / 1024
        result["tracemalloc_peak_kb"] = peak / 1024
    else:
        result["tracemalloc_current_kb"] = 0
        result["tracemalloc_peak_kb"] = 0
    
    result["global_data_store_size"] = len(_global_data_store)
    result["global_callback_list_size"] = len(_global_callback_list)
    
    count0, count1, count2 = gc.get_count()
    result["gc_gen0_count"] = count0
    result["gc_gen1_count"] = count1
    result["gc_gen2_count"] = count2
    
    if prefix:
        print(f"\n{'='*60}")
        print(f"内存探针: {prefix}")
        print(f"{'='*60}")
        print(f"  tracemalloc 当前: {result['tracemalloc_current_kb']:.2f} KB")
        print(f"  tracemalloc 峰值: {result['tracemalloc_peak_kb']:.2f} KB")
        print(f"  全局数据存储: {result['global_data_store_size']} 项")
        print(f"  全局回调列表: {result['global_callback_list_size']} 项")
        print(f"  GC计数: gen0={result['gc_gen0_count']}, gen1={result['gc_gen1_count']}, gen2={result['gc_gen2_count']}")
    
    return result


def add_to_global_store(key: str, obj: DataObject):
    """添加对象到全局存储（只加不删 - 泄漏模式）"""
    _global_data_store[key] = obj


def remove_from_global_store(key: str):
    """从全局存储移除对象（正常清理）"""
    if key in _global_data_store:
        del _global_data_store[key]


def register_callback(callback: CallbackObject):
    """注册回调到全局列表（只注册不注销 - 泄漏模式）"""
    _global_callback_list.append(callback)


def unregister_callback(callback: CallbackObject):
    """从全局列表注销回调（正常清理）"""
    if callback in _global_callback_list:
        _global_callback_list.remove(callback)


def clear_global_containers():
    """清空所有全局容器（完整清理）"""
    _global_data_store.clear()
    _global_callback_list.clear()


def run_container_leak_demo():
    """
    运行容器持有导致的内存泄漏演示
    
    场景:
    1. 在全局容器中添加大量对象（只加不删）
    2. 使用内存探针记录状态
    3. 清理操作后再次记录状态
    4. 对比清理前后的差异
    """
    print("=" * 70)
    print("容器持有导致的内存泄漏演示")
    print("=" * 70)
    
    DataObject._id_counter = 0
    CallbackObject._id_counter = 0
    clear_global_containers()
    gc.collect()
    
    print("\n[阶段1] 初始化 tracemalloc")
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()
    
    probe_before = memory_probe("初始状态 (空容器)")
    
    print("\n" + "-" * 60)
    print("[阶段2] 向全局容器添加大量对象（只加不删模式）")
    print("-" * 60)
    
    weak_refs = []
    
    for i in range(100):
        data_obj = DataObject(f"data_{i}", size=50)
        add_to_global_store(f"key_{i}", data_obj)
        weak_refs.append(weakref.ref(data_obj))
        
        if i % 10 == 0:
            callback_obj = CallbackObject(f"callback_{i}")
            register_callback(callback_obj)
            weak_refs.append(weakref.ref(callback_obj))
    
    print(f"  已添加: {len(_global_data_store)} 个数据对象")
    print(f"  已添加: {len(_global_callback_list)} 个回调对象")
    print(f"  弱引用总数: {len(weak_refs)}")
    
    actual_surviving = sum(1 for ref in weak_refs if ref() is not None)
    print(f"  实际存活对象数: {actual_surviving}")
    
    probe_adding = memory_probe("添加对象后 (泄漏模式)")
    
    print("\n" + "-" * 60)
    print("[阶段3] 删除局部变量，但全局容器仍持有引用")
    print("-" * 60)
    
    del data_obj
    if 'callback_obj' in dir():
        del callback_obj
    
    gc.collect()
    
    actual_surviving = sum(1 for ref in weak_refs if ref() is not None)
    print(f"  删除局部变量后实际存活对象数: {actual_surviving} (应为全部存活)")
    
    probe_after_del_local = memory_probe("删除局部变量后")
    
    print("\n" + "-" * 60)
    print("[阶段4] 执行GC（无法回收被容器持有的对象）")
    print("-" * 60)
    
    collected = gc.collect()
    print(f"  GC回收对象数: {collected}")
    
    actual_surviving = sum(1 for ref in weak_refs if ref() is not None)
    print(f"  GC后实际存活对象数: {actual_surviving} (容器持有导致无法回收)")
    
    probe_after_gc = memory_probe("GC后 (容器仍持有)")
    
    print("\n" + "-" * 60)
    print("[阶段5] 清理全局容器（真正的清理操作）")
    print("-" * 60)
    
    clear_global_containers()
    collected = gc.collect()
    
    print(f"  清空容器后GC回收对象数: {collected}")
    
    actual_surviving = sum(1 for ref in weak_refs if ref() is not None)
    print(f"  清理后实际存活对象数: {actual_surviving} (应为0或接近0)")
    
    probe_after_cleanup = memory_probe("清理全局容器后")
    
    print("\n" + "=" * 70)
    print("对比分析汇总")
    print("=" * 70)
    
    print(f"\n{'阶段':<25} {'数据对象':<10} {'回调对象':<10} {'当前内存KB':<15} {'峰值内存KB':<15}")
    print(f"{'-'*25} {'-'*10} {'-'*10} {'-'*15} {'-'*15}")
    
    stages = [
        ("初始状态", probe_before),
        ("添加对象后", probe_adding),
        ("删除局部变量", probe_after_del_local),
        ("GC后(仍持有)", probe_after_gc),
        ("清理容器后", probe_after_cleanup),
    ]
    
    for name, probe in stages:
        print(f"{name:<25} "
              f"{probe['global_data_store_size']:<10} "
              f"{probe['global_callback_list_size']:<10} "
              f"{probe['tracemalloc_current_kb']:<15.2f} "
              f"{probe['tracemalloc_peak_kb']:<15.2f}")
    
    print("\n" + "=" * 70)
    print("tracemalloc 分配统计 (Top 5)")
    print("=" * 70)
    
    snapshot2 = tracemalloc.take_snapshot()
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    for index, stat in enumerate(top_stats[:5], 1):
        frame = stat.traceback[0]
        print(f"\n  #{index}: {frame.filename}:{frame.lineno}")
        print(f"     大小: {stat.size_diff / 1024:.2f} KB ({stat.size_diff:+} 字节)")
        print(f"     计数: {stat.count_diff:+} 个对象")
    
    tracemalloc.stop()
    
    print("\n" + "=" * 70)
    print("关键结论")
    print("=" * 70)
    print("1. 全局容器持有是最常见的内存泄漏模式之一")
    print("2. 即使删除局部变量，只要容器仍持有引用，对象就不会被回收")
    print("3. GC无法回收被活跃引用持有的对象（引用计数不为0）")
    print("4. tracemalloc 是定位这类泄漏的有效工具")
    print("5. 解决方案: 及时从容器移除、使用弱引用、设置缓存淘汰策略")
    
    return {
        "before": probe_before,
        "after_leak": probe_adding,
        "after_cleanup": probe_after_cleanup
    }


def run_weakref_vs_strongref_container():
    """
    对比：强引用容器 vs 弱引用容器
    
    展示使用弱引用如何避免容器持有导致的泄漏
    """
    print("\n" + "=" * 70)
    print("对比: 强引用容器 vs 弱引用容器")
    print("=" * 70)
    
    DataObject._id_counter = 0
    gc.collect()
    
    strong_container = []
    weak_container = weakref.WeakKeyDictionary()
    
    tracemalloc.start()
    
    print("\n[强引用容器测试]")
    probe1 = memory_probe("强引用容器 - 初始")
    
    strong_refs = []
    for i in range(50):
        obj = DataObject(f"strong_{i}", size=30)
        strong_container.append(obj)
        strong_refs.append(weakref.ref(obj))
    
    probe2 = memory_probe("强引用容器 - 添加后")
    
    print(f"\n  删除局部变量前存活: {sum(1 for r in strong_refs if r() is not None)}")
    del obj
    del strong_container
    gc.collect()
    print(f"  删除局部变量后存活: {sum(1 for r in strong_refs if r() is not None)} (容器也被删除)")
    
    probe3 = memory_probe("强引用容器 - 删除后")
    
    print("\n[弱引用容器测试]")
    probe4 = memory_probe("弱引用容器 - 初始")
    
    weak_refs = []
    objects_holder = []
    for i in range(50):
        obj = DataObject(f"weak_{i}", size=30)
        weak_container[obj] = i
        objects_holder.append(obj)
        weak_refs.append(weakref.ref(obj))
    
    probe5 = memory_probe("弱引用容器 - 添加后")
    print(f"\n  弱引用容器大小: {len(weak_container)}")
    print(f"  实际存活对象数: {sum(1 for r in weak_refs if r() is not None)}")
    
    print("\n  删除业务对象持有者...")
    del objects_holder
    del obj
    gc.collect()
    
    probe6 = memory_probe("弱引用容器 - 删除业务对象后")
    print(f"\n  弱引用容器大小: {len(weak_container)} (应为0或接近0)")
    print(f"  实际存活对象数: {sum(1 for r in weak_refs if r() is not None)}")
    
    tracemalloc.stop()
    
    print("\n" + "=" * 70)
    print("对比总结")
    print("=" * 70)
    print("1. 强引用容器: 容器持有 = 对象存活，必须手动清理")
    print("2. 弱引用容器: 容器持有不影响对象生命周期")
    print("   - 当业务侧不再引用对象时，对象自动被回收")
    print("   - 弱引用容器不会导致内存泄漏")
    
    gc.collect()


if __name__ == "__main__":
    run_container_leak_demo()
    run_weakref_vs_strongref_container()
