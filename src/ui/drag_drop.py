"""Native Windows file-drop support without third-party dependencies."""

from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any


class WindowsFileDrop:
    """Register WM_DROPFILES on a Tk/CustomTkinter root window."""

    WM_DROPFILES = 0x0233
    GWLP_WNDPROC = -4

    def __init__(self, root: Any, callback: Callable[[list[Path]], None]) -> None:
        self._root = root
        self._callback = callback
        self._old_proc: int | None = None
        self._proc_reference: Any = None
        self._hwnd: int | None = None

    def register(self) -> bool:
        """Enable native file dropping on Windows."""
        if os.name != "nt":
            return False
        self._root.update_idletasks()
        hwnd = int(self._root.winfo_id())
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        long_ptr = ctypes.c_ssize_t
        hwnd_type = ctypes.c_void_p
        wparam_type = ctypes.c_size_t
        lparam_type = ctypes.c_ssize_t
        get_window_long = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
        set_window_long = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
        get_window_long.argtypes = [hwnd_type, ctypes.c_int]
        get_window_long.restype = long_ptr
        set_window_long.argtypes = [hwnd_type, ctypes.c_int, long_ptr]
        set_window_long.restype = long_ptr
        user32.CallWindowProcW.argtypes = [long_ptr, hwnd_type, ctypes.c_uint, wparam_type, lparam_type]
        user32.CallWindowProcW.restype = long_ptr
        shell32.DragAcceptFiles.argtypes = [hwnd_type, ctypes.c_bool]
        shell32.DragAcceptFiles.restype = None
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
        shell32.DragQueryFileW.restype = ctypes.c_uint
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        shell32.DragFinish.restype = None

        window_proc_type = ctypes.WINFUNCTYPE(
            long_ptr,
            hwnd_type,
            ctypes.c_uint,
            wparam_type,
            lparam_type,
        )
        old_proc = int(get_window_long(hwnd_type(hwnd), self.GWLP_WNDPROC))
        if not old_proc:
            raise OSError("Unable to read the existing Windows window procedure.")

        @window_proc_type
        def window_proc(window: int, message: int, wparam: int, lparam: int) -> int:
            if message == self.WM_DROPFILES:
                drop_handle = ctypes.c_void_p(wparam)
                count = shell32.DragQueryFileW(drop_handle, 0xFFFFFFFF, None, 0)
                paths: list[Path] = []
                try:
                    for index in range(count):
                        length = shell32.DragQueryFileW(drop_handle, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(drop_handle, index, buffer, length + 1)
                        paths.append(Path(buffer.value))
                finally:
                    shell32.DragFinish(drop_handle)
                self._root.after(0, lambda captured=paths: self._callback(captured))
                return 0
            return int(user32.CallWindowProcW(long_ptr(old_proc), window, message, wparam, lparam))

        callback_pointer = ctypes.cast(window_proc, ctypes.c_void_p).value
        if callback_pointer is None:
            raise OSError("Unable to create the Windows drop callback pointer.")
        shell32.DragAcceptFiles(hwnd_type(hwnd), True)
        previous = int(set_window_long(hwnd_type(hwnd), self.GWLP_WNDPROC, long_ptr(callback_pointer)))
        if not previous:
            shell32.DragAcceptFiles(hwnd_type(hwnd), False)
            raise OSError("Unable to install the Windows drop callback.")
        self._old_proc = old_proc
        self._proc_reference = window_proc
        self._hwnd = hwnd
        return True

    def unregister(self) -> None:
        """Restore the original window procedure when registered."""
        if os.name != "nt" or self._old_proc is None or self._hwnd is None:
            return
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        long_ptr = ctypes.c_ssize_t
        hwnd_type = ctypes.c_void_p
        set_window_long = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
        set_window_long.argtypes = [hwnd_type, ctypes.c_int, long_ptr]
        set_window_long.restype = long_ptr
        shell32.DragAcceptFiles.argtypes = [hwnd_type, ctypes.c_bool]
        shell32.DragAcceptFiles.restype = None
        set_window_long(hwnd_type(self._hwnd), self.GWLP_WNDPROC, long_ptr(self._old_proc))
        shell32.DragAcceptFiles(hwnd_type(self._hwnd), False)
        self._old_proc = None
        self._proc_reference = None
        self._hwnd = None
