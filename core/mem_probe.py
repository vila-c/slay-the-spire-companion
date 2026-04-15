"""
JVM Memory Probe for Slay the Spire
------------------------------------
原理：
  STS 用 Java 8 HotSpot JVM，对象头固定格式。
  通过扫描 JVM heap segment 中的已知字节特征
  定位 AbstractPlayer / AbstractRoom 对象。

用法：
  1. 先启动 STS 并进入游戏
  2. 运行此脚本（需要管理员权限）
  3. 输出找到的数据
"""

import struct
import time
import ctypes
import sys
import pymem
import pymem.process


# ─── 工具函数 ────────────────────────────────────────────

def read_int(pm, addr):
    """读取 4 字节有符号整数"""
    try:
        return pm.read_int(addr)
    except Exception:
        return None


def read_long(pm, addr):
    """读取 8 字节整数（JVM 指针）"""
    try:
        return pm.read_longlong(addr)
    except Exception:
        return None


def read_bytes(pm, addr, size):
    try:
        return pm.read_bytes(addr, size)
    except Exception:
        return None


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


# ─── JVM Heap 扫描 ───────────────────────────────────────

def get_java_process(pm):
    """获取 java.exe 进程信息"""
    try:
        proc = pymem.process.process_from_name("java.exe")
        return proc
    except Exception:
        return None


def scan_memory_for_pattern(pm, pattern: bytes, region_start, region_size, step=4):
    """在指定内存区域扫描字节模式，返回所有命中地址"""
    results = []
    chunk_size = 0x10000  # 64KB 块读取

    offset = 0
    while offset < region_size:
        read_size = min(chunk_size, region_size - offset)
        addr = region_start + offset
        chunk = read_bytes(pm, addr, read_size)
        if chunk:
            idx = 0
            while True:
                pos = chunk.find(pattern, idx)
                if pos == -1:
                    break
                results.append(addr + pos)
                idx = pos + step
        offset += chunk_size

    return results


def find_heap_regions(pm):
    """枚举 JVM heap 内存区域（大块 commit 内存）"""
    import ctypes
    import ctypes.wintypes

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress",       ctypes.c_ulonglong),
            ("AllocationBase",    ctypes.c_ulonglong),
            ("AllocationProtect", ctypes.wintypes.DWORD),
            ("RegionSize",        ctypes.c_ulonglong),
            ("State",             ctypes.wintypes.DWORD),
            ("Protect",           ctypes.wintypes.DWORD),
            ("Type",              ctypes.wintypes.DWORD),
        ]

    MEM_COMMIT  = 0x1000
    PAGE_READWRITE = 0x04
    MEM_PRIVATE = 0x20000

    regions = []
    addr = 0x10000
    mbi = MEMORY_BASIC_INFORMATION()

    while addr < 0x7FFFFFFFFFFF:
        size = ctypes.windll.kernel32.VirtualQueryEx(
            pm.process_handle,
            ctypes.c_ulonglong(addr),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi)
        )
        if size == 0:
            break

        # 只关注大块 private commit RW 内存（JVM heap 特征）
        if (mbi.State == MEM_COMMIT and
            mbi.Protect == PAGE_READWRITE and
            mbi.Type == MEM_PRIVATE and
            mbi.RegionSize >= 0x100000):  # >= 1MB
            regions.append((mbi.BaseAddress, mbi.RegionSize))

        addr = mbi.BaseAddress + mbi.RegionSize
        if addr <= mbi.BaseAddress:
            break

    return regions


# ─── 特征定位策略 ────────────────────────────────────────

# Java String "Ironclad" 在 JVM heap 中的 UTF-16 编码
# HotSpot Java 8: String.value 是 char[]（UTF-16LE）
CHARACTER_NAMES = {
    "铁甲战士": "Ironclad",
    "沉默猎手": "THE_SILENT",  # 内部名
    "机械傀儡": "DEFECT",
    "观察者":   "WATCHER",
}

# 在 heap 中搜索角色名 ASCII 字节
def find_character_strings(pm, regions):
    """搜索角色类名字符串，推断玩家对象位置"""
    targets = [b"Ironclad", b"THE_SILENT", b"DEFECT", b"WATCHER"]
    found = {}

    print("[扫描] 搜索角色名字符串...")
    for base, size in regions:
        for target in targets:
            hits = scan_memory_for_pattern(pm, target, base, size)
            if hits:
                name = target.decode()
                if name not in found:
                    found[name] = []
                found[name].extend(hits[:5])  # 只保留前5个

    return found


# ─── 读取附近的 HP 值 ────────────────────────────────────

def probe_nearby_ints(pm, addr, radius=256):
    """读取地址附近的整数，寻找合理的 HP 值（1-999范围）"""
    results = []
    for offset in range(-radius, radius, 4):
        val = read_int(pm, addr + offset)
        if val is not None and 1 <= val <= 999:
            results.append((offset, val))
    return results


# ─── 主逻辑 ─────────────────────────────────────────────

def main():
    if not is_admin():
        print("[错误] 需要管理员权限运行")
        print("       右键 -> 以管理员身份运行")
        input("按 Enter 退出...")
        sys.exit(1)

    print("=" * 50)
    print("STS JVM 内存探针 v0.1")
    print("=" * 50)

    # 连接进程
    try:
        pm = pymem.Pymem("javaw.exe")
        print(f"[OK] 已连接 javaw.exe，PID: {pm.process_id}")
    except Exception as e:
        print(f"[错误] 找不到 javaw.exe: {e}")
        print("       请先启动 STS 并进入游戏")
        input("按 Enter 退出...")
        return

    # 枚举 heap 区域
    print("[扫描] 枚举 JVM heap 内存区域...")
    regions = find_heap_regions(pm)
    total_mb = sum(s for _, s in regions) // (1024 * 1024)
    print(f"[OK] 找到 {len(regions)} 个区域，共 {total_mb} MB")

    # 搜索角色字符串
    found = find_character_strings(pm, regions)

    if not found:
        print("[失败] 未找到角色名字符串，请确认游戏已进入战斗或地图界面")
        input("按 Enter 退出...")
        return

    print(f"\n[结果] 找到以下角色名地址：")
    for name, addrs in found.items():
        for addr in addrs:
            print(f"  {name}: 0x{addr:X}")
            # 读取附近整数，寻找 HP
            nearby = probe_nearby_ints(pm, addr, 512)
            if nearby:
                print(f"    附近合理整数（可能是 HP）:")
                for off, val in nearby[:10]:
                    print(f"      offset {off:+d}: {val}")

    # 保存原始探针结果供进一步分析
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mem_probe_result.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"区域数量: {len(regions)}\n\n")
        for name, addrs in found.items():
            for addr in addrs:
                f.write(f"{name}: 0x{addr:X}\n")
                nearby = probe_nearby_ints(pm, addr, 512)
                for off, val in nearby:
                    f.write(f"  offset {off:+d}: {val}\n")

    print(f"\n[已保存] {output_path}")
    input("\n按 Enter 退出...")


if __name__ == "__main__":
    main()
