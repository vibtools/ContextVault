"""Frozen one-window ContextVault desktop interface."""

from __future__ import annotations

import logging
import queue
import time
import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image

from src.config.constants import DEFAULT_WINDOW_SIZE, MINIMUM_WINDOW_SIZE
from src.controllers.application_controller import ApplicationController
from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings
from src.models.tasks import ApplicationEvent, EventType
from src.services.logging_service import LoggingService
from src.ui import theme
from src.ui.drag_drop import WindowsFileDrop
from src.ui.pages import (
    AboutPage,
    ArchivesPage,
    ConversationsPage,
    DashboardPage,
    HistoryPage,
    LogsPage,
    SettingsPage,
)
from src.utils.paths import asset_path
from src.utils.system import ProcessMetrics

LOGGER = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Render all frozen pages and marshal worker events onto the UI thread."""

    def __init__(self, controller: ApplicationController, logging_service: LoggingService) -> None:
        super().__init__(fg_color=theme.BACKGROUND)
        self.controller = controller
        self.logging_service = logging_service
        self.title("ContextVault")
        self.geometry(DEFAULT_WINDOW_SIZE)
        self.minsize(*MINIMUM_WINDOW_SIZE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._current_task_id: str | None = None
        self._progress_task_id: str | None = None
        self._progress_started_at: float | None = None
        self._browser_connected = False
        self._process_metrics = ProcessMetrics()
        self._notification_after_id: str | None = None
        self._notification_frame: ctk.CTkFrame | None = None
        self._drop_handler = WindowsFileDrop(self, self._handle_drop)
        self._image_references: list[Any] = []

        self._build_toolbar()
        self._build_sidebar()
        self._build_workspace()
        self._build_bottom_area()
        self._bind_shortcuts()
        try:
            self._drop_handler.register()
        except (OSError, AttributeError, RuntimeError):
            LOGGER.exception("Native drag-and-drop registration failed")
        self.after(100, self._poll_events)
        self.after(200, self._poll_logs)
        self.after(1000, self._update_metrics)
        self.after(300, self.controller.refresh_archives)
        self.after(350, self.controller.refresh_history)
        self.show_page("Dashboard")

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, height=58, fg_color=theme.CARD, corner_radius=0, border_color=theme.BORDER, border_width=1)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)
        icon = self._load_image("icons/icon.png", (34, 34))
        ctk.CTkLabel(toolbar, text="ContextVault", image=icon, compound="left", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=16, pady=10)
        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=2, padx=10, pady=8)
        for text, command in (
            ("Launch Chrome", self._run(self.controller.launch_browser)),
            ("Connect", self._run(self.controller.connect_browser)),
            ("Scan", self._run(self.controller.scan_conversations)),
            ("Refresh", self._run(self.controller.refresh_browser)),
            ("Close", self._run(self.controller.close_browser)),
        ):
            ctk.CTkButton(actions, text=text, width=105, command=command).pack(side="left", padx=4)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=190, fg_color=theme.CARD, corner_radius=0, border_color=theme.BORDER, border_width=1)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        for index, name in enumerate(("Dashboard", "Conversations", "Archives", "Export History", "Settings", "Logs", "About")):
            button = ctk.CTkButton(
                sidebar,
                text=name,
                anchor="w",
                fg_color="transparent",
                hover_color=theme.BORDER,
                command=lambda page=name: self.show_page(page),
            )
            button.grid(row=index, column=0, padx=10, pady=(12 if index == 0 else 4, 4), sticky="ew")
            self._nav_buttons[name] = button

    def _build_workspace(self) -> None:
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.grid(row=1, column=1, padx=14, pady=14, sticky="nsew")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)
        settings = self.controller.get_settings()
        self.pages: dict[str, ctk.CTkFrame] = {
            "Dashboard": DashboardPage(self.workspace),
            "Conversations": ConversationsPage(
                self.workspace,
                self._export_selected,
                self._export_all,
                self._run(self.controller.scan_conversations),
                self._open_conversation,
                self._copy_url,
            ),
            "Archives": ArchivesPage(
                self.workspace,
                self._view_archive,
                self._open_archive_folder,
                self._delete_archive,
                self._rebuild_summary,
                self._validate_archive,
                self._run(self.controller.refresh_archives),
            ),
            "Export History": HistoryPage(self.workspace, self._run(self.controller.refresh_history)),
            "Settings": SettingsPage(self.workspace, settings, self._save_settings),
            "Logs": LogsPage(self.workspace),
            "About": AboutPage(self.workspace),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _build_bottom_area(self) -> None:
        bottom = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=0, border_color=theme.BORDER, border_width=1)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew")
        bottom.grid_columnconfigure(1, weight=1)
        self.status_var = tk.StringVar(value="Browser: Disconnected | Worker: 0 | CPU: 0% | Memory: 0 MB | Queue: 0 | Current: Idle")
        ctk.CTkLabel(bottom, textvariable=self.status_var, anchor="w", text_color=theme.MUTED).grid(row=0, column=0, columnspan=4, padx=12, pady=(8, 2), sticky="ew")
        self.progress_label = tk.StringVar(value="Ready")
        ctk.CTkLabel(bottom, textvariable=self.progress_label, anchor="w").grid(row=1, column=0, padx=12, pady=(2, 8))
        self.progress = ctk.CTkProgressBar(bottom)
        self.progress.set(0)
        self.progress.grid(row=1, column=1, padx=8, pady=(2, 8), sticky="ew")
        self.progress_detail = tk.StringVar(value="0%")
        ctk.CTkLabel(bottom, textvariable=self.progress_detail, width=70).grid(row=1, column=2, padx=4, pady=(2, 8))
        ctk.CTkButton(bottom, text="Cancel", width=80, fg_color=theme.DANGER, hover_color="#B91C1C", command=self._cancel_export).grid(row=1, column=3, padx=(4, 6), pady=(2, 8))
        ctk.CTkButton(bottom, text="Resume", width=80, command=self._resume_export).grid(row=1, column=4, padx=(0, 12), pady=(2, 8))

    def show_page(self, name: str) -> None:
        page = self.pages[name]
        page.tkraise()
        for page_name, button in self._nav_buttons.items():
            button.configure(fg_color=theme.PRIMARY if page_name == name else "transparent")
        if name == "Archives":
            self.controller.refresh_archives()
        elif name == "Export History":
            self.controller.refresh_history()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-f>", lambda _event: self._focus_conversation_search())
        self.bind_all("<Control-e>", lambda _event: self._export_selected())
        self.bind_all("<Control-a>", lambda _event: self._select_all())
        self.bind_all("<Control-r>", lambda _event: self._run_task(self.controller.scan_conversations))
        self.bind_all("<Control-comma>", lambda _event: self.show_page("Settings"))
        self.bind_all("<F5>", lambda _event: self._run_task(self.controller.refresh_browser))
        self.bind_all("<Escape>", lambda _event: self._cancel_export())

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.controller.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle_event(self, event: ApplicationEvent) -> None:
        if event.task_id:
            self._current_task_id = event.task_id
        payload = event.payload
        if event.event_type == EventType.PROGRESS:
            percentage = float(payload.get("percentage", 0.0))
            if event.task_id != self._progress_task_id:
                self._progress_task_id = event.task_id
                self._progress_started_at = time.monotonic()
            self.progress.set(percentage / 100.0)
            self.progress_label.set(str(payload.get("stage") or "Working"))
            self.progress_detail.set(self._format_progress_detail(payload, percentage))
        elif event.event_type == EventType.CONVERSATIONS:
            items = [ConversationListItem.model_validate(item) for item in payload.get("items", [])]
            page = self.pages["Conversations"]
            assert isinstance(page, ConversationsPage)
            page.set_items(items)
            dashboard = self.pages["Dashboard"]
            assert isinstance(dashboard, DashboardPage)
            dashboard.update_value("Conversations", str(len(items)))
        elif event.event_type == EventType.ARCHIVES:
            items = list(payload.get("items", []))
            page = self.pages["Archives"]
            assert isinstance(page, ArchivesPage)
            page.set_items(items)
            dashboard = self.pages["Dashboard"]
            assert isinstance(dashboard, DashboardPage)
            dashboard.update_value("Archives", str(len(items)))
        elif event.event_type == EventType.HISTORY:
            items = list(payload.get("items", []))
            page = self.pages["Export History"]
            assert isinstance(page, HistoryPage)
            page.set_items(items)
            if items:
                dashboard = self.pages["Dashboard"]
                assert isinstance(dashboard, DashboardPage)
                dashboard.update_value("Last Export", str(items[0].get("exportedAt", "Today")))
        elif event.event_type == EventType.BROWSER:
            self._browser_connected = bool(payload.get("connected"))
            dashboard = self.pages["Dashboard"]
            assert isinstance(dashboard, DashboardPage)
            dashboard.update_value("Status", "Connected" if self._browser_connected else "Disconnected")
        elif event.event_type == EventType.NOTIFICATION:
            self._show_notification(str(payload.get("message") or "Notification"), str(payload.get("level") or "info"))
        elif event.event_type == EventType.ERROR:
            self._show_notification(str(payload.get("message") or "Task failed"), "error")
            self.progress_label.set("Failed")
            self._finish_progress_tracking(event.task_id)
        elif event.event_type == EventType.COMPLETED:
            self.progress.set(1.0)
            self.progress_label.set("Completed")
            elapsed = self._elapsed_progress_seconds(event.task_id)
            self.progress_detail.set(
                "100%" if elapsed is None else f"100% · {self._format_duration(elapsed)} elapsed"
            )
            self._finish_progress_tracking(event.task_id)
        elif event.event_type == EventType.STATUS:
            state = str(payload.get("state") or "")
            if state == "started":
                self._progress_task_id = event.task_id
                self._progress_started_at = time.monotonic()
                self.progress.set(0.0)
                self.progress_label.set(str(payload.get("name") or "Working"))
                self.progress_detail.set("0%")
            elif state == "cancelled":
                self.progress_label.set("Cancelled")
                self._finish_progress_tracking(event.task_id)
                self._show_notification("Export cancelled. Resume is available for the current session.", "warning")

    def _format_progress_detail(self, payload: dict[str, Any], percentage: float) -> str:
        parts = [f"{percentage:.0f}%"]
        completed = int(payload.get("completedItems") or 0)
        total = int(payload.get("totalItems") or 0)
        elapsed = self._elapsed_progress_seconds(self._progress_task_id) or 0.0
        if total > 0:
            parts.append(f"{completed}/{total}")
        if completed > 0 and elapsed > 0:
            parts.append(f"{completed / elapsed:.1f} items/s")
        eta_value = payload.get("etaSeconds")
        eta: float | None
        try:
            eta = float(eta_value) if eta_value is not None else None
        except (TypeError, ValueError):
            eta = None
        if eta is None and 0.0 < percentage < 100.0 and elapsed > 0:
            eta = elapsed * (100.0 - percentage) / percentage
        if eta is not None and eta >= 0:
            parts.append(f"ETA {self._format_duration(eta)}")
        current_item = str(payload.get("currentItem") or "")
        if current_item:
            parts.append(current_item)
        return " · ".join(parts)

    def _elapsed_progress_seconds(self, task_id: str | None) -> float | None:
        if task_id != self._progress_task_id or self._progress_started_at is None:
            return None
        return max(0.0, time.monotonic() - self._progress_started_at)

    def _finish_progress_tracking(self, task_id: str | None) -> None:
        if task_id == self._progress_task_id:
            self._progress_task_id = None
            self._progress_started_at = None

    @staticmethod
    def _format_duration(seconds: float) -> str:
        bounded = max(0, int(round(seconds)))
        minutes, remaining = divmod(bounded, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}h {minutes:02d}m"
        if minutes:
            return f"{minutes:d}m {remaining:02d}s"
        return f"{remaining:d}s"

    def _poll_logs(self) -> None:
        page = self.pages["Logs"]
        assert isinstance(page, LogsPage)
        try:
            for _ in range(200):
                page.append(self.logging_service.ui_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(200, self._poll_logs)

    def _update_metrics(self) -> None:
        cpu, memory = self._process_metrics.sample()
        queue_count = self.controller.task_manager.active_count()
        dashboard = self.pages["Dashboard"]
        assert isinstance(dashboard, DashboardPage)
        dashboard.update_value("Queue", str(queue_count))
        current = self.progress_label.get()
        self.status_var.set(
            f"Browser: {'Connected' if self._browser_connected else 'Disconnected'} | "
            f"Worker: {self.controller.get_settings().performance.worker_threads} | CPU: {cpu:.0f}% | "
            f"Memory: {memory / (1024 * 1024):.0f} MB | Queue: {queue_count} | Current: {current}"
        )
        self.after(1000, self._update_metrics)

    def _run(self, function: Any) -> Any:
        return lambda: self._run_task(function)

    def _run_task(self, function: Any) -> None:
        try:
            task_id = function()
            if isinstance(task_id, str):
                self._current_task_id = task_id
        except Exception as exc:
            LOGGER.exception("UI command failed")
            self._show_notification(str(exc), "error")

    def _export_selected(self, items: list[ConversationListItem] | None = None) -> None:
        page = self.pages["Conversations"]
        assert isinstance(page, ConversationsPage)
        selected = items if items is not None else page.selected_items()
        self._run_task(lambda: self.controller.export_conversations(selected))

    def _export_all(self, items: list[ConversationListItem]) -> None:
        self._run_task(lambda: self.controller.export_conversations(items))

    def _focus_conversation_search(self) -> None:
        self.show_page("Conversations")
        page = self.pages["Conversations"]
        assert isinstance(page, ConversationsPage)
        page.focus_search()

    def _select_all(self) -> None:
        self.show_page("Conversations")
        page = self.pages["Conversations"]
        assert isinstance(page, ConversationsPage)
        page.select_all()

    def _open_conversation(self, item: ConversationListItem) -> None:
        self._run_task(lambda: self.controller.open_conversation(item))

    def _copy_url(self, url: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(url)
        self._show_notification("Conversation URL copied.", "success")

    def _view_archive(self, path: Path) -> None:
        if not self.controller.open_archive(path):
            self._show_notification("Unable to open archive Markdown.", "error")

    def _open_archive_folder(self, path: Path) -> None:
        if not self.controller.open_archive_folder(path):
            self._show_notification("Unable to open archive folder.", "error")

    def _delete_archive(self, path: Path) -> None:
        self._run_task(lambda: self.controller.delete_archive(path))

    def _rebuild_summary(self, path: Path) -> None:
        self._run_task(lambda: self.controller.rebuild_summary(path))

    def _validate_archive(self, path: Path) -> None:
        self._run_task(lambda: self.controller.validate_archive(path))

    def _save_settings(self, settings: ApplicationSettings) -> None:
        self._run_task(lambda: self.controller.save_settings(settings))

    def _cancel_export(self) -> None:
        if not self.controller.cancel_export():
            self._show_notification("No active export can be cancelled.", "warning")

    def _resume_export(self) -> None:
        self._run_task(self.controller.resume_export)

    def _show_notification(self, message: str, level: str) -> None:
        self._dismiss_notification()
        color = {"success": theme.SUCCESS, "warning": theme.WARNING, "error": theme.DANGER}.get(level, theme.PRIMARY)
        frame = ctk.CTkFrame(self, fg_color=theme.CARD, border_color=color, border_width=2)
        frame.place(relx=0.99, y=68, anchor="ne")
        ctk.CTkLabel(frame, text=message, wraplength=360, justify="left").pack(padx=14, pady=12)
        self._notification_frame = frame
        self._notification_after_id = self.after(4500, self._dismiss_notification)

    def _dismiss_notification(self) -> None:
        after_id = self._notification_after_id
        self._notification_after_id = None
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        frame = self._notification_frame
        self._notification_frame = None
        if frame is not None:
            try:
                if frame.winfo_exists():
                    frame.destroy()
            except tk.TclError:
                pass

    def _handle_drop(self, paths: list[Path]) -> None:
        archive_paths = [path for path in paths if path.is_dir() and (path / "manifest.json").is_file()]
        if not archive_paths:
            self._show_notification("Dropped item is not a ContextVault archive folder.", "warning")
            return
        self.show_page("Archives")
        archive_path = archive_paths[0]
        if self.controller.open_archive(archive_path):
            self._show_notification("Archive opened and validation started.", "success")
        else:
            self._show_notification("Archive detected, but conversation.md could not be opened.", "warning")
        self._validate_archive(archive_path)

    def _load_image(self, relative_path: str, size: tuple[int, int]) -> ctk.CTkImage | None:
        path = asset_path(relative_path)
        if not path.is_file():
            return None
        with Image.open(path) as source_image:
            image = source_image.copy()
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        self._image_references.extend([image, ctk_image])
        return ctk_image

    def _close(self) -> None:
        try:
            self._dismiss_notification()
            self._drop_handler.unregister()
            self.controller.shutdown()
        except Exception:
            LOGGER.exception("Application shutdown encountered an error")
        finally:
            self.destroy()

