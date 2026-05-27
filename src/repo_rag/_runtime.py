from __future__ import annotations

import os
import sys

_APPLIED = False


def _full_speed() -> bool:
    v = os.environ.get("RAG_FULL_SPEED", "").strip().lower()
    return v not in ("", "0", "false", "no", "off")


def _thread_count_default() -> int:
    cpu = os.cpu_count() or 4
    if _full_speed():
        return min(cpu, 8)
    return max(2, min(4, cpu // 3))


def _disable_affinity() -> bool:
    v = os.environ.get("RAG_DISABLE_AFFINITY", "").strip().lower()
    return v not in ("", "0", "false", "no", "off")


def _set_windows_low_priority_and_affinity(skip_first_n_cpus: int = 4) -> dict:
    """Lower CPU priority and pin to non-P-core CPUs.

    Uses BELOW_NORMAL_PRIORITY_CLASS instead of PROCESS_MODE_BACKGROUND_BEGIN.
    Background mode also forces IDLE I/O priority, which causes model files
    in %TEMP% to never finish loading because Windows Defender realtime
    scanning has higher I/O priority and preempts indefinitely.

    Pinning to higher logical CPUs avoids the Intel hybrid P-cores (Windows
    places P-cores at logical CPUs 0..N-1 on most modern laptops).
    """
    result = {"low_priority": False, "affinity": False, "affinity_mask": None}
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetPriorityClass.restype = wintypes.BOOL
        kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        kernel32.SetProcessAffinityMask.restype = wintypes.BOOL

        handle = kernel32.GetCurrentProcess()

        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        if kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS):
            result["low_priority"] = True

        if not _disable_affinity():
            cpu = os.cpu_count() or 4
            if cpu > skip_first_n_cpus + 1:
                mask = 0
                for i in range(skip_first_n_cpus, cpu):
                    mask |= 1 << i
                if kernel32.SetProcessAffinityMask(handle, mask):
                    result["affinity"] = True
                    result["affinity_mask"] = hex(mask)
    except Exception:
        pass
    return result


_set_windows_background_and_affinity = _set_windows_low_priority_and_affinity


def apply_runtime_tuning(threads: int | None = None, low_priority: bool = True) -> dict:
    global _APPLIED
    if _APPLIED:
        return {"already_applied": True}
    _APPLIED = True

    if threads is None:
        env_val = os.environ.get("RAG_INDEX_THREADS")
        if env_val:
            try:
                threads = max(1, int(env_val))
            except ValueError:
                threads = _thread_count_default()
        else:
            threads = _thread_count_default()

    n = str(threads)
    os.environ.setdefault("OMP_NUM_THREADS", n)
    os.environ.setdefault("MKL_NUM_THREADS", n)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", n)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", n)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    info = {"threads": threads, "low_priority": False, "affinity": False}
    full_speed = _full_speed()
    if full_speed:
        info["full_speed"] = True
        return info
    if low_priority and sys.platform == "win32":
        info.update(_set_windows_low_priority_and_affinity())
    elif low_priority and hasattr(os, "nice"):
        try:
            os.nice(10)
            info["low_priority"] = True
        except Exception:
            pass

    return info


def force_threads(threads: int) -> None:
    n = str(max(1, int(threads)))
    os.environ["OMP_NUM_THREADS"] = n
    os.environ["MKL_NUM_THREADS"] = n
    os.environ["OPENBLAS_NUM_THREADS"] = n
    os.environ["NUMEXPR_NUM_THREADS"] = n


def release_background_mode() -> dict:
    """Restore NORMAL priority + full affinity so the process runs at full speed.

    Used by --full-speed when the user has chosen to run the rebuild alone on an
    idle system and wants maximum throughput.
    """
    result = {"released_priority": False, "released_affinity": False}
    if sys.platform != "win32":
        return result
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetPriorityClass.restype = wintypes.BOOL
        kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        kernel32.SetProcessAffinityMask.restype = wintypes.BOOL

        handle = kernel32.GetCurrentProcess()
        NORMAL_PRIORITY_CLASS = 0x00000020
        if kernel32.SetPriorityClass(handle, NORMAL_PRIORITY_CLASS):
            result["released_priority"] = True

        cpu = os.cpu_count() or 4
        mask = (1 << cpu) - 1
        if kernel32.SetProcessAffinityMask(handle, mask):
            result["released_affinity"] = True
    except Exception:
        pass
    return result
