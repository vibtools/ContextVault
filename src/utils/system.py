"""Portable process metrics and operating-system integration."""

from __future__ import annotations

import ctypes
import os
import platform
import time
import webbrowser
from ctypes import wintypes
from pathlib import Path


class ProcessMetrics:
    """Low-overhead CPU and memory sampler without external dependencies."""

    def __init__(self) -> None:
        self._last_wall_time = time.perf_counter()
        self._last_cpu_time = time.process_time()

    def sample(self) -> tuple[float, int]:
        """Return process CPU percentage and resident memory bytes."""
        wall_now = time.perf_counter()
        cpu_now = time.process_time()
        wall_delta = max(wall_now - self._last_wall_time, 1e-9)
        cpu_delta = max(cpu_now - self._last_cpu_time, 0.0)
        self._last_wall_time = wall_now
        self._last_cpu_time = cpu_now
        cpu_percent = min(100.0, (cpu_delta / wall_delta) * 100.0)
        return cpu_percent, process_memory_bytes()


def process_memory_bytes() -> int:
    """Return current process resident memory where supported."""
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return int(counters.WorkingSetSize)
        return 0

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(usage * (1 if platform.system() == "Darwin" else 1024))
    except (ImportError, ValueError, OSError):
        return 0


def open_path(path: Path) -> bool:
    """Open a file or directory using the operating system's registered handler."""
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return False
    if os.name == "nt":
        os.startfile(str(resolved))  # type: ignore[attr-defined]
        return True
    return webbrowser.open(resolved.as_uri())
