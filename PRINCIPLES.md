# Python 内存管理与GC原理

本文档简要说明本演示项目涉及的核心概念。

---

## 一、引用计数 (Reference Counting)

### 基本原理
Python 中每个对象都有一个引用计数，表示有多少个引用指向它。

```python
a = [1, 2, 3]    # 引用计数 = 1
b = a             # 引用计数 = 2
del a             # 引用计数 = 1
del b             # 引用计数 = 0 → 对象被回收
```

### 优点
1. 简单直观
2. 实时回收（引用计数为0时立即回收）
3. 暂停时间可预测

### 致命缺点：循环引用
```python
a = {}
b = {}
a['other'] = b    # a 引用 b
b['other'] = a    # b 引用 a
del a
del b
# 此时 a 和 b 的引用计数仍为 1（互相引用）
# 但外部已无法访问它们 → 内存泄漏！
```

---

## 二、分代垃圾回收 (Generational GC)

### 为什么需要分代GC？
引用计数无法处理循环引用，因此 Python 引入了分代GC作为补充。

### 弱代假说 (Weak Generational Hypothesis)
1. **大多数对象寿命很短**（朝生夕死）
2. **存活越久的对象，越不可能成为垃圾**

### 三代结构
```
┌─────────────────────────────────────────────────────────┐
│  第2代 (老年代)                                           │
│  - 第1代GC后存活的对象                                    │
│  - GC最少，只在阈值触发或显式调用时执行                    │
│  - 存放长期存活的对象                                      │
├─────────────────────────────────────────────────────────┤
│  第1代 (中年代)                                           │
│  - 第0代GC后存活的对象                                    │
│  - GC频率较低                                             │
├─────────────────────────────────────────────────────────┤
│  第0代 (年轻代)                                           │
│  - 新创建的对象                                            │
│  - GC最频繁（对象数量超过阈值时触发）                       │
│  - 大多数对象在这里创建和死亡                               │
└─────────────────────────────────────────────────────────┘
```

### 阈值控制
```python
import gc
gc.get_threshold()  # (700, 10, 10)
# 第0代对象数 > 700 → 触发第0代GC
# 第0代GC次数 > 10 → 触发第1代GC
# 第1代GC次数 > 10 → 触发第2代GC
```

### GC做什么？
1. **检测循环引用**：遍历对象图，找出不可达的循环引用组
2. **移动存活对象**：将存活对象晋升到下一代
3. **回收垃圾**：释放不可达对象的内存

---

## 三、常见内存泄漏模式

### 模式1: 全局容器只加不删
```python
# 泄漏模式
_cache = {}

def add_data(key, value):
    _cache[key] = value  # 只添加，从不清理

# 正确模式
def add_data(key, value):
    _cache[key] = value
    if len(_cache) > 1000:
        # LRU淘汰或定期清理
        _cleanup_old_entries()
```

### 模式2: 循环引用
```python
# 泄漏模式
class Node:
    def __init__(self):
        self.parent = None
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)
        child.parent = self  # 形成循环引用！

# 解决方案：弱引用
import weakref

class Node:
    def __init__(self):
        self._parent_ref = None
        self.children = []
    
    @property
    def parent(self):
        return self._parent_ref() if self._parent_ref else None
    
    def add_child(self, child):
        self.children.append(child)
        child._parent_ref = weakref.ref(self)  # 弱引用
```

### 模式3: 回调/监听器只注册不注销
```python
# 泄漏模式
class EventManager:
    _listeners = []
    
    @classmethod
    def register(cls, listener):
        cls._listeners.append(listener)

# 正确模式：提供注销方法 + 弱引用
class EventManager:
    _listeners = []
    
    @classmethod
    def register(cls, listener):
        cls._listeners.append(weakref.ref(listener))
    
    @classmethod
    def notify(cls, event):
        # 自动清理已死亡的弱引用
        cls._listeners = [r for r in cls._listeners if r() is not None]
        for ref in cls._listeners:
            ref()(event)
```

---

## 四、线上排查思路

### 1. 初步诊断
```bash
# 检查进程内存趋势
ps -p <pid> -o pid,rss,cmd --no-headers

# 或使用 top/htop 观察内存增长
```

### 2. tracemalloc（Python标准库）
```python
import tracemalloc

tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()

# ... 执行业务代码 ...

snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

for stat in top_stats[:10]:
    print(stat)
```

### 3. objgraph（第三方工具）
```python
import objgraph

# 查看对象类型数量增长
objgraph.show_growth()

# 查找特定类型对象的引用链
objgraph.find_backref(some_object, max_depth=10)

# 生成引用图（需要graphviz）
objgraph.show_chain(
    objgraph.find_backref_chain(
        some_object,
        objgraph.is_proper_module
    )
)
```

### 4. gc模块诊断
```python
import gc

# 查看GC统计
gc.get_stats()

# 启用调试模式（检测泄漏）
gc.set_debug(gc.DEBUG_LEAK)

# 手动执行GC
gc.collect()

# 查看不可回收对象（通常是循环引用且有__del__的对象）
gc.garbage
```

### 5. 排查步骤总结
```
1. 确认内存泄漏 → 观察进程RSS是否持续增长
       ↓
2. 定位泄漏类型 → tracemalloc 对比快照
       ↓
3. 查找泄漏源 → objgraph 分析引用链
       ↓
4. 验证修复 → 对比修复前后的内存趋势
```

---

## 五、关键要点

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 循环引用 | 引用计数无法处理互相引用 | 弱引用(weakref)、手动断链 |
| 全局容器泄漏 | 对象被长期持有 | 定期清理、弱引用容器、LRU淘汰 |
| 回调泄漏 | 监听器只注册不注销 | 弱引用回调、提供注销方法 |
| 无法定位泄漏 | 不知道哪里分配了内存 | tracemalloc、objgraph |

---

## 运行演示

```bash
# 查看所有子命令
python -m mem_gc_demo

# 循环引用与弱引用对比
python -m mem_gc_demo cyclic-refs

# 分代GC演示
python -m mem_gc_demo gen-gc

# 容器泄漏演示
python -m mem_gc_demo container-leak

# 运行所有演示
python -m mem_gc_demo all
```
