"""
分代垃圾回收机制演示

Python的分代GC基于"弱代假说":
1. 大多数对象生命周期很短（朝生夕死）
2. 存活时间越长的对象，越不可能成为垃圾

分代GC策略:
- 第0代 (年轻代): 新创建的对象，GC最频繁
- 第1代 (中年代): 第0代GC后存活的对象
- 第2代 (老年代): 第1代GC后存活的对象，GC最少

阈值控制 (gc.get_threshold()):
- 阈值(0): 第0代对象数量阈值，超过则触发第0代GC
- 阈值(1): 第0代GC次数阈值，超过则触发第1代GC
- 阈值(2): 第1代GC次数阈值，超过则触发第2代GC
"""

import gc
import sys
import weakref


class ShortLivedObject:
    """短寿命对象 - 用于观察分代GC"""
    _id_counter = 0
    
    def __init__(self, value: int = 0):
        self.id = ShortLivedObject._id_counter
        ShortLivedObject._id_counter += 1
        self.value = value
        self.data = [i for i in range(10)]


def print_generation_stats(prefix: str = ""):
    """打印各代GC统计信息"""
    count0, count1, count2 = gc.get_count()
    thresh0, thresh1, thresh2 = gc.get_threshold()
    if prefix:
        print(f"\n{prefix}")
    print(f"  第0代: {count0}/{thresh0} 对象")
    print(f"  第1代: {count1}/{thresh1} 次扫描")
    print(f"  第2代: {count2}/{thresh2} 次扫描")


def print_collection_summary(collected: int, prefix: str = ""):
    """打印GC回收摘要"""
    if prefix:
        print(f"\n{prefix}")
    print(f"  回收对象数: {collected}")
    
    stats = gc.get_stats()
    for i, gen_stats in enumerate(stats):
        print(f"  第{i}代统计:")
        print(f"    收集次数: {gen_stats.get('collections', 0)}")
        print(f"    回收对象: {gen_stats.get('collected', 0)}")
        print(f"    不可回收: {gen_stats.get('uncollectable', 0)}")


def run_generational_demo(batch_count: int = 5, 
                          batch_size: int = 100,
                          force_collect: bool = False):
    """
    分代GC演示
    
    参数:
        batch_count: 批次数量
        batch_size: 每批创建的对象数量
        force_collect: 每批结束时是否强制调用 gc.collect()
    """
    print("=" * 70)
    print(f"分代GC演示 (force_collect={force_collect})")
    print("=" * 70)
    print(f"配置: {batch_count} 批次 x {batch_size} 个对象/批次")
    print(f"GC阈值初始值: {gc.get_threshold()}")

    gc.set_debug(0)
    gc.collect()
    
    ShortLivedObject._id_counter = 0
    
    print_generation_stats("初始状态")
    
    surviving_refs = []
    
    for batch in range(batch_count):
        print(f"\n{'='*50}")
        print(f"批次 {batch + 1}/{batch_count}")
        print(f"{'='*50}")
        
        print_generation_stats(f"批次开始前")
        
        batch_objects = []
        for i in range(batch_size):
            obj = ShortLivedObject(batch * batch_size + i)
            batch_objects.append(obj)
            
            if i % 10 == 0:
                surviving_refs.append(weakref.ref(obj))
        
        print(f"\n  创建了 {len(batch_objects)} 个对象")
        print(f"  存活弱引用数: {len(surviving_refs)}")
        
        actual_surviving = sum(1 for ref in surviving_refs if ref() is not None)
        print(f"  实际存活对象数: {actual_surviving}")
        
        print_generation_stats(f"创建对象后")
        
        print(f"\n  删除批次局部引用...")
        del batch_objects
        
        actual_surviving = sum(1 for ref in surviving_refs if ref() is not None)
        print(f"  删除后实际存活对象数: {actual_surviving}")
        
        if force_collect:
            print(f"\n  强制调用 gc.collect()...")
            collected = gc.collect()
            print_collection_summary(collected, "GC摘要")
        else:
            print(f"\n  不强制GC，让自动GC触发...")
        
        print_generation_stats(f"批次结束时")
        
        actual_surviving = sum(1 for ref in surviving_refs if ref() is not None)
        print(f"\n  当前实际存活对象数: {actual_surviving}")

    print("\n" + "=" * 70)
    print("最终状态")
    print("=" * 70)
    
    actual_surviving = sum(1 for ref in surviving_refs if ref() is not None)
    print(f"\n  总存活弱引用数: {len(surviving_refs)}")
    print(f"  实际存活对象数: {actual_surviving}")
    
    print_generation_stats("最终GC计数")
    
    print("\n执行完整GC...")
    collected = gc.collect()
    print_collection_summary(collected, "完整GC摘要")
    
    actual_surviving = sum(1 for ref in surviving_refs if ref() is not None)
    print(f"\n  完整GC后实际存活对象数: {actual_surviving}")
    
    return {
        "force_collect": force_collect,
        "total_created": ShortLivedObject._id_counter,
        "final_surviving": actual_surviving
    }


def run_comparison():
    """
    运行对比测试：force_collect=True vs force_collect=False
    
    展示两种策略下的分代GC行为差异
    """
    print("=" * 70)
    print("对比测试: 强制GC vs 不强制GC")
    print("=" * 70)
    
    print("\n" + "="*70)
    print("测试1: 不强制GC (依赖自动GC)")
    print("="*70)
    
    result1 = run_generational_demo(
        batch_count=3, 
        batch_size=50, 
        force_collect=False
    )
    
    print("\n" + "="*70)
    print("测试2: 每批后强制GC")
    print("="*70)
    
    result2 = run_generational_demo(
        batch_count=3, 
        batch_size=50, 
        force_collect=True
    )
    
    print("\n" + "="*70)
    print("对比结果汇总")
    print("="*70)
    
    print(f"\n{'测试场景':<25} {'创建对象':<12} {'最终存活':<12}")
    print(f"{'-'*25} {'-'*12} {'-'*12}")
    print(f"{'不强制GC':<25} {result1['total_created']:<12} {result1['final_surviving']:<12}")
    print(f"{'每批强制GC':<25} {result2['total_created']:<12} {result2['final_surviving']:<12}")
    
    print("\n关键观察:")
    print("1. 不强制GC时，对象可能在多代中累积，直到触发自动GC")
    print("2. 强制GC会立即回收垃圾对象，但可能影响性能")
    print("3. 分代GC的核心是: 年轻代频繁GC，老年代很少GC")
    
    gc.collect()


if __name__ == "__main__":
    run_comparison()
