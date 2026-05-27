import ctypes
import sys
from ctypes import wintypes

sys.path.insert(0, r"C:\Raptor\rag tool\src")

from repo_rag._runtime import apply_runtime_tuning

r = apply_runtime_tuning()
print(f"Runtime tuning result: {r}")

k = ctypes.windll.kernel32
k.GetCurrentProcess.restype = wintypes.HANDLE
k.GetPriorityClass.argtypes = [wintypes.HANDLE]
k.GetPriorityClass.restype = wintypes.DWORD
k.GetProcessAffinityMask.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(ctypes.c_size_t),
]
k.GetProcessAffinityMask.restype = wintypes.BOOL
h = k.GetCurrentProcess()
prio = k.GetPriorityClass(h)
proc_mask = ctypes.c_size_t()
sys_mask = ctypes.c_size_t()
k.GetProcessAffinityMask(h, ctypes.byref(proc_mask), ctypes.byref(sys_mask))
print(f"Priority class: 0x{prio:X}  (IDLE=0x40, BELOW_NORMAL=0x4000, NORMAL=0x20)")
print(f"Affinity mask:  0x{proc_mask.value:X}  (system: 0x{sys_mask.value:X})")
print(f"CPUs allowed:   {bin(proc_mask.value).count('1')}")
