"""CustomTkinter page implementations for the frozen one-window UI."""

from __future__ import annotations

import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable

import customtkinter as ctk
from pydantic import ValidationError

from src.config.constants import APPLICATION_VERSION

from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings
from src.ui import theme
from src.utils.system import open_path


class DashboardPage(ctk.CTkFrame):
    """Application status overview cards."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)
        self._values: dict[str, ctk.CTkLabel] = {}
        cards = [
            ("Browser", "Chrome"),
            ("Status", "Disconnected"),
            ("Conversations", "0"),
            ("Archives", "0"),
            ("Last Export", "Never"),
            ("Queue", "0"),
        ]
        for index, (title, value) in enumerate(cards):
            frame = ctk.CTkFrame(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
            frame.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(frame, text=title, text_color=theme.MUTED, font=ctk.CTkFont(size=14)).pack(anchor="w", padx=18, pady=(16, 4))
            label = ctk.CTkLabel(frame, text=value, text_color=theme.TEXT, font=ctk.CTkFont(size=25, weight="bold"))
            label.pack(anchor="w", padx=18, pady=(0, 16))
            self._values[title] = label

    def update_value(self, name: str, value: str) -> None:
        label = self._values.get(name)
        if label is not None:
            label.configure(text=value)


class ConversationsPage(ctk.CTkFrame):
    """Searchable conversation selection and preview page."""

    def __init__(
        self,
        master: Any,
        on_export_selected: Callable[[list[ConversationListItem]], None],
        on_export_all: Callable[[list[ConversationListItem]], None],
        on_refresh: Callable[[], None],
        on_open: Callable[[ConversationListItem], None],
        on_copy_url: Callable[[str], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self._on_export_selected = on_export_selected
        self._on_export_all = on_export_all
        self._on_refresh = on_refresh
        self._on_open = on_open
        self._on_copy_url = on_copy_url
        self._items: list[ConversationListItem] = []
        self._variables: dict[str, tk.BooleanVar] = {}
        self._selected_item: ConversationListItem | None = None

        left = ctk.CTkFrame(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
        left.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(left, textvariable=self.search_var, placeholder_text="Search conversations")
        self.search_entry.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        self.search_var.trace_add("write", lambda *_: self._render_items())
        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)
        button_bar = ctk.CTkFrame(left, fg_color="transparent")
        button_bar.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        button_bar.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(button_bar, text="Export Selected", command=self.export_selected).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(button_bar, text="Export All", command=self.export_all).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(button_bar, text="Refresh", command=self._on_refresh).grid(row=0, column=2, padx=4, sticky="ew")

        right = ctk.CTkFrame(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
        right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        ctk.CTkLabel(right, text="Conversation Preview", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=18, pady=(18, 12))
        self.preview_vars: dict[str, tk.StringVar] = {}
        for field in ("Title", "URL", "Messages", "Images", "Code", "Attachments", "Estimated Size"):
            row = ctk.CTkFrame(right, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(row, text=field, width=110, anchor="w", text_color=theme.MUTED).pack(side="left")
            variable = tk.StringVar(value="—")
            ctk.CTkLabel(row, textvariable=variable, anchor="w", justify="left", wraplength=330).pack(side="left", fill="x", expand=True)
            self.preview_vars[field] = variable
        ctk.CTkButton(right, text="Export", command=self.export_selected).pack(fill="x", padx=18, pady=18)

        self._context_menu = tk.Menu(self, tearoff=False)
        self._context_menu.add_command(label="Export", command=self.export_selected)
        self._context_menu.add_command(label="Open", command=self._open_selected)
        self._context_menu.add_command(label="Copy URL", command=self._copy_selected_url)
        self._context_menu.add_command(label="View Metadata", command=self._show_metadata)
        self._context_menu.add_command(label="Refresh", command=self._on_refresh)
        self._context_menu.add_command(label="Delete Archive", state="disabled")

    def set_items(self, items: list[ConversationListItem]) -> None:
        """Replace scanned conversations while preserving matching selections."""
        previous = {key for key, variable in self._variables.items() if variable.get()}
        self._items = list(items)
        self._variables = {
            item.conversation_id: tk.BooleanVar(value=item.conversation_id in previous)
            for item in self._items
        }
        self._render_items()

    def selected_items(self) -> list[ConversationListItem]:
        selected: list[ConversationListItem] = []
        for item in self._items:
            variable = self._variables.get(item.conversation_id)
            if variable is not None and variable.get():
                selected.append(item)
        return selected

    def select_all(self) -> None:
        for variable in self._variables.values():
            variable.set(True)

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def export_selected(self) -> None:
        self._on_export_selected(self.selected_items())

    def export_all(self) -> None:
        self._on_export_all(list(self._items))

    def _render_items(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        query = self.search_var.get().strip().lower()
        row_index = 0
        for item in self._items:
            if query and query not in item.title.lower() and query not in item.url.lower():
                continue
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.grid(row=row_index, column=0, sticky="ew", padx=2, pady=2)
            row.grid_columnconfigure(1, weight=1)
            checkbox = ctk.CTkCheckBox(row, text="", width=24, variable=self._variables[item.conversation_id])
            checkbox.grid(row=0, column=0, padx=(4, 2), pady=6)
            label = ctk.CTkLabel(row, text=item.title, anchor="w", justify="left", wraplength=430)
            label.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
            label.bind("<Button-1>", lambda _event, selected=item: self._select_item(selected))
            label.bind("<Double-Button-1>", lambda _event, selected=item: self._on_open(selected))
            label.bind("<Button-3>", lambda event, selected=item: self._show_context_menu(event, selected))
            row_index += 1

    def _select_item(self, item: ConversationListItem) -> None:
        self._selected_item = item
        self.preview_vars["Title"].set(item.title)
        self.preview_vars["URL"].set(item.url)
        self.preview_vars["Messages"].set(str(item.message_count) if item.message_count is not None else "Unknown until export")
        self.preview_vars["Images"].set(str(item.image_count) if item.image_count is not None else "Unknown until export")
        self.preview_vars["Code"].set(str(item.code_count) if item.code_count is not None else "Unknown until export")
        self.preview_vars["Attachments"].set(str(item.attachment_count) if item.attachment_count is not None else "Unknown until export")
        self.preview_vars["Estimated Size"].set(_format_size(item.estimated_size) if item.estimated_size is not None else "Unknown until export")

    def _show_context_menu(self, event: tk.Event[Any], item: ConversationListItem) -> None:
        self._select_item(item)
        self._context_menu.tk_popup(event.x_root, event.y_root)

    def _open_selected(self) -> None:
        if self._selected_item is not None:
            self._on_open(self._selected_item)

    def _copy_selected_url(self) -> None:
        if self._selected_item is not None:
            self._on_copy_url(self._selected_item.url)

    def _show_metadata(self) -> None:
        if self._selected_item is None:
            return
        messagebox.showinfo(
            "Conversation Metadata",
            f"Title: {self._selected_item.title}\nID: {self._selected_item.conversation_id}\nURL: {self._selected_item.url}",
            parent=self,
        )


class ArchivesPage(ctk.CTkFrame):
    """Archive manager with selection-gated actions and manifest preview."""

    def __init__(
        self,
        master: Any,
        on_view: Callable[[Path], None],
        on_preview: Callable[[Path], None],
        on_open_folder: Callable[[Path], None],
        on_rename: Callable[[Path, str], None],
        on_delete: Callable[[Path], None],
        on_rebuild: Callable[[Path], None],
        on_validate: Callable[[Path], None],
        on_refresh: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self._on_view = on_view
        self._on_preview = on_preview
        self._on_open_folder = on_open_folder
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._on_rebuild = on_rebuild
        self._on_validate = on_validate
        self._on_refresh = on_refresh
        self._selected: dict[str, Any] | None = None
        self._row_frames: dict[str, ctk.CTkFrame] = {}
        self._action_buttons: dict[str, ctk.CTkButton] = {}
        self._preview_generation = 0
        self._preview_queue: deque[tuple[str, str, Any]] = deque()

        ctk.CTkLabel(
            self,
            text="Archive Manager",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, padx=(0, 8), sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.list_frame = ctk.CTkScrollableFrame(
            left,
            fg_color=theme.CARD,
            border_color=theme.BORDER,
            border_width=1,
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for column in range(4):
            bar.grid_columnconfigure(column, weight=1)
        actions = [
            ("View", self._view_selected),
            ("Preview", self._preview_selected),
            ("Open Folder", self._open_folder_selected),
            ("Edit", self._rename_selected),
            ("Delete", self._delete_selected),
            ("Rebuild Summary", self._rebuild_selected),
            ("Validate", self._validate_selected),
        ]
        for index, (text, command) in enumerate(actions):
            button = ctk.CTkButton(bar, text=text, command=command, width=110, state="disabled")
            button.grid(row=index // 4, column=index % 4, padx=4, pady=4, sticky="ew")
            self._action_buttons[text] = button
        ctk.CTkButton(bar, text="Refresh", command=self._refresh, width=110).grid(
            row=1,
            column=3,
            padx=4,
            pady=4,
            sticky="ew",
        )

        preview = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            border_color=theme.BORDER,
            border_width=1,
        )
        preview.grid(row=1, column=1, padx=(8, 0), sticky="nsew")
        preview.grid_rowconfigure(1, weight=1)
        preview.grid_columnconfigure(0, weight=1)
        self.preview_title = tk.StringVar(value="Manifest Preview")
        ctk.CTkLabel(
            preview,
            textvariable=self.preview_title,
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 8), sticky="ew")

        style = ttk.Style(self)
        style.configure(
            "ContextVault.Treeview",
            background=theme.CARD,
            fieldbackground=theme.CARD,
            foreground=theme.TEXT,
            bordercolor=theme.BORDER,
            rowheight=24,
        )
        style.configure(
            "ContextVault.Treeview.Heading",
            background=theme.BORDER,
            foreground=theme.TEXT,
        )
        style.map(
            "ContextVault.Treeview",
            background=[("selected", theme.PRIMARY)],
            foreground=[("selected", theme.TEXT)],
        )
        self.preview_tree = ttk.Treeview(
            preview,
            columns=("value",),
            show="tree headings",
            style="ContextVault.Treeview",
        )
        self.preview_tree.heading("#0", text="Key")
        self.preview_tree.heading("value", text="Value")
        self.preview_tree.column("#0", width=220, stretch=True)
        self.preview_tree.column("value", width=260, stretch=True)
        vertical = ttk.Scrollbar(preview, orient="vertical", command=self.preview_tree.yview)
        horizontal = ttk.Scrollbar(preview, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.preview_tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 0))
        vertical.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 0))
        horizontal.grid(row=2, column=0, sticky="ew", padx=(12, 0), pady=(0, 12))
        self._show_empty_preview("Select an archive and click Preview.")

    def set_items(self, items: list[dict[str, Any]]) -> None:
        """Replace the filesystem-backed list and clear stale selection state."""
        self._selected = None
        self._set_actions_enabled(False)
        self._row_frames.clear()
        self._show_empty_preview("Select an archive and click Preview.")
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not items:
            ctk.CTkLabel(
                self.list_frame,
                text="No archive folders were found.",
                text_color=theme.MUTED,
            ).grid(row=0, column=0, padx=16, pady=20, sticky="w")
            return
        for index, item in enumerate(items):
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.grid(row=index, column=0, padx=6, pady=4, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            archive_name = str(item.get("name") or Path(str(item.get("path") or "")).name)
            conversation_title = str(item.get("title") or archive_name)
            name_label = ctk.CTkLabel(
                row,
                text=archive_name,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            )
            name_label.grid(row=0, column=0, padx=8, pady=(7, 0), sticky="ew")
            title_label = ctk.CTkLabel(
                row,
                text=conversation_title,
                anchor="w",
                text_color=theme.MUTED,
            )
            title_label.grid(row=1, column=0, padx=8, pady=(0, 7), sticky="ew")
            status = ctk.CTkLabel(
                row,
                text=str(item.get("status") or "unknown"),
                text_color=theme.MUTED,
            )
            status.grid(row=0, column=1, rowspan=2, padx=8)
            size = ctk.CTkLabel(
                row,
                text=_format_size(int(item.get("size") or 0)),
                text_color=theme.MUTED,
            )
            size.grid(row=0, column=2, rowspan=2, padx=8)
            path_key = str(item.get("path") or "")
            self._row_frames[path_key] = row
            for widget in (row, name_label, title_label, status, size):
                widget.bind("<Button-1>", lambda _event, selected=item: self._select(selected))
                widget.bind("<Double-Button-1>", lambda _event, selected=item: self._double_click(selected))

    def set_preview(self, archive_name: str, manifest: dict[str, Any]) -> None:
        """Render a manifest payload incrementally to keep the UI responsive."""
        self._preview_generation += 1
        generation = self._preview_generation
        self.preview_title.set(f"Manifest Preview — {archive_name}")
        self._clear_preview_tree()
        root_id = self.preview_tree.insert("", "end", text="manifest.json", values=("",), open=True)
        self._preview_queue = deque((root_id, str(key), value) for key, value in manifest.items())
        self.after_idle(lambda: self._drain_preview_queue(generation))

    def _drain_preview_queue(self, generation: int) -> None:
        if generation != self._preview_generation:
            return
        processed = 0
        while self._preview_queue and processed < 200:
            parent, key, value = self._preview_queue.popleft()
            processed += 1
            if isinstance(value, dict):
                item_id = self.preview_tree.insert(parent, "end", text=key, values=("object",))
                self._preview_queue.extend((item_id, str(child_key), child) for child_key, child in value.items())
            elif isinstance(value, list):
                item_id = self.preview_tree.insert(parent, "end", text=key, values=(f"list[{len(value)}]",))
                self._preview_queue.extend((item_id, f"[{index}]", child) for index, child in enumerate(value))
            else:
                self.preview_tree.insert(parent, "end", text=key, values=(_preview_scalar(value),))
        if self._preview_queue:
            self.after(1, lambda: self._drain_preview_queue(generation))

    def _show_empty_preview(self, message: str) -> None:
        self._preview_generation += 1
        self._preview_queue.clear()
        self.preview_title.set("Manifest Preview")
        self._clear_preview_tree()
        self.preview_tree.insert("", "end", text=message, values=("",))

    def _clear_preview_tree(self) -> None:
        children = self.preview_tree.get_children()
        if children:
            self.preview_tree.delete(*children)

    def _select(self, item: dict[str, Any]) -> None:
        self._selected = item
        selected_path = str(item.get("path") or "")
        for path, row in self._row_frames.items():
            row.configure(fg_color=theme.BORDER if path == selected_path else "transparent")
        self._set_actions_enabled(True)

    def _double_click(self, item: dict[str, Any]) -> None:
        self._select(item)
        self._on_view(Path(str(item["path"])))

    def _selected_path(self) -> Path | None:
        if self._selected is None:
            messagebox.showwarning("Archive Manager", "Select an archive first.", parent=self)
            return None
        return Path(str(self._selected["path"]))

    def _view_selected(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._on_view(path)

    def _preview_selected(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._on_preview(path)

    def _open_folder_selected(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._on_open_folder(path)

    def _rename_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        current_name = str(self._selected.get("name") or path.name) if self._selected else path.name
        new_name = simpledialog.askstring(
            "Rename Archive",
            "Archive folder name:",
            initialvalue=current_name,
            parent=self,
        )
        if new_name is None or new_name.strip() == current_name:
            return
        self._on_rename(path, new_name.strip())

    def _delete_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        display_name = str(self._selected.get("name") or path.name) if self._selected else path.name
        if messagebox.askyesno("Delete Archive", f"Delete '{display_name}'?", parent=self):
            self._on_delete(path)

    def _rebuild_selected(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._on_rebuild(path)

    def _validate_selected(self) -> None:
        path = self._selected_path()
        if path is not None:
            self._on_validate(path)

    def _refresh(self) -> None:
        self._selected = None
        self._set_actions_enabled(False)
        self._show_empty_preview("Refreshing archive folders…")
        self._on_refresh()

    def _set_actions_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self._action_buttons.values():
            button.configure(state=state)


class HistoryPage(ctk.CTkFrame):
    """Read-only export history page."""

    def __init__(self, master: Any, on_refresh: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="Export History", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Refresh", width=100, command=on_refresh).pack(side="right")
        self.textbox = ctk.CTkTextbox(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self.textbox.configure(state="disabled")

    def set_items(self, items: list[dict[str, Any]]) -> None:
        lines = []
        for item in items:
            lines.append(
                f"{item.get('exportedAt', '')} | {item.get('status', '')} | {item.get('title', '')}\n"
                f"  {item.get('archivePath', '')}\n"
            )
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "\n".join(lines) if lines else "No exports recorded.")
        self.textbox.configure(state="disabled")


class SettingsPage(ctk.CTkFrame):
    """Validated UI settings page."""

    def __init__(self, master: Any, settings: ApplicationSettings, on_save: Callable[[ApplicationSettings], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_save = on_save
        self._variables: dict[str, tk.Variable] = {}
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        content = ctk.CTkScrollableFrame(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)
        row = 0
        row = self._section(content, row, "Browser")
        self._variables["browser"] = tk.StringVar(value="Chrome")
        self._option(content, row, "Browser", self._variables["browser"], ["Chrome"]); row += 1
        self._variables["user_data_dir"] = tk.StringVar(value=settings.browser.user_data_dir)
        self._variables["profile_directory"] = tk.StringVar(value=settings.browser.profile_directory)
        self._profile_folder_entry(
            content,
            row,
            "Browser Profile Root",
            self._variables["user_data_dir"],
            self._variables["profile_directory"],
        ); row += 1
        self._entry(content, row, "Profile", self._variables["profile_directory"]); row += 1
        self._variables["cdp_endpoint"] = tk.StringVar(value=settings.browser.cdp_endpoint)
        self._entry(content, row, "CDP Endpoint", self._variables["cdp_endpoint"]); row += 1

        row = self._section(content, row, "Export")
        self._variables["default_folder"] = tk.StringVar(value=settings.export.default_folder)
        self._folder_entry(content, row, "Default Folder", self._variables["default_folder"]); row += 1
        self._variables["archive_name"] = tk.StringVar(value=settings.export.archive_name)
        self._entry(content, row, "Archive Name", self._variables["archive_name"]); row += 1
        for key, label, value in (
            ("auto_create_folder", "Auto Create Folder", settings.export.auto_create_folder),
            ("overwrite", "Overwrite", settings.export.overwrite),
            ("compress", "Compress", settings.export.compress),
            ("verify_export", "Verify Export", settings.export.verify_export),
        ):
            self._variables[key] = tk.BooleanVar(value=value)
            self._switch(content, row, label, self._variables[key]); row += 1

        row = self._section(content, row, "Assets")
        for key, label, value, editable in (
            ("images", "Images", settings.assets.images, True),
            ("code", "Code", settings.assets.code, True),
            ("tables", "Tables", settings.assets.tables, True),
            ("attachments", "Download Attachments", settings.assets.attachments, True),
            ("markdown", "Markdown", True, False),
            ("json", "JSON", True, False),
            ("summary", "Summary", settings.assets.summary, True),
            ("statistics", "Statistics", True, False),
            ("search_index", "Search Index", settings.assets.search_index, True),
        ):
            self._variables[key] = tk.BooleanVar(value=value)
            self._checkbox(content, row, label, self._variables[key], editable); row += 1

        row = self._section(content, row, "Performance")
        self._variables["worker_threads"] = tk.StringVar(value=str(settings.performance.worker_threads))
        self._option(content, row, "Worker Threads", self._variables["worker_threads"], ["1", "2", "4", "8"]); row += 1
        self._variables["message_retry_count"] = tk.StringVar(value=str(settings.performance.message_retry_count))
        self._entry(content, row, "Message Retry Count", self._variables["message_retry_count"]); row += 1
        self._variables["delay_mode"] = tk.StringVar(value=settings.performance.delay_mode)
        self._option(content, row, "Delay", self._variables["delay_mode"], ["Auto", "Fast", "Normal", "Safe"]); row += 1
        self._variables["memory_mode"] = tk.StringVar(value=settings.performance.memory_mode)
        self._option(content, row, "Memory", self._variables["memory_mode"], ["Low", "Balanced", "High"]); row += 1
        ctk.CTkButton(content, text="Save Settings", command=self._save).grid(row=row, column=0, columnspan=3, padx=16, pady=18, sticky="ew")

    def _save(self) -> None:
        try:
            settings = ApplicationSettings.model_validate(
                {
                    "schemaVersion": "1.0",
                    "browser": {
                        "browser": "Chrome",
                        "userDataDir": self._variables["user_data_dir"].get(),
                        "profileDirectory": self._variables["profile_directory"].get(),
                        "cdpEndpoint": self._variables["cdp_endpoint"].get(),
                        "startUrl": "https://chatgpt.com/",
                    },
                    "export": {
                        "defaultFolder": self._variables["default_folder"].get(),
                        "archiveName": self._variables["archive_name"].get(),
                        "autoCreateFolder": self._variables["auto_create_folder"].get(),
                        "overwrite": self._variables["overwrite"].get(),
                        "compress": self._variables["compress"].get(),
                        "verifyExport": self._variables["verify_export"].get(),
                    },
                    "assets": {key: self._variables[key].get() for key in ("images", "code", "tables", "attachments", "markdown", "json", "summary", "statistics", "search_index")},
                    "performance": {
                        "workerThreads": int(str(self._variables["worker_threads"].get())),
                        "messageRetryCount": int(str(self._variables["message_retry_count"].get())),
                        "delayMode": self._variables["delay_mode"].get(),
                        "memoryMode": self._variables["memory_mode"].get(),
                    },
                }
            )
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Invalid Settings", str(exc), parent=self)
            return
        self._on_save(settings)

    @staticmethod
    def _section(master: Any, row: int, title: str) -> int:
        ctk.CTkLabel(master, text=title, font=ctk.CTkFont(size=18, weight="bold")).grid(row=row, column=0, columnspan=3, padx=16, pady=(18, 8), sticky="w")
        return row + 1

    @staticmethod
    def _entry(master: Any, row: int, label: str, variable: tk.Variable) -> None:
        ctk.CTkLabel(master, text=label, anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        ctk.CTkEntry(master, textvariable=variable).grid(row=row, column=1, columnspan=2, padx=16, pady=6, sticky="ew")

    @staticmethod
    def _folder_entry(master: Any, row: int, label: str, variable: tk.Variable) -> None:
        ctk.CTkLabel(master, text=label, anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        ctk.CTkEntry(master, textvariable=variable).grid(row=row, column=1, padx=(16, 6), pady=6, sticky="ew")
        ctk.CTkButton(master, text="Select Folder", width=110, command=lambda: _select_folder(variable)).grid(row=row, column=2, padx=(6, 16), pady=6)

    @staticmethod
    def _profile_folder_entry(
        master: Any,
        row: int,
        label: str,
        root_variable: tk.Variable,
        profile_variable: tk.Variable,
    ) -> None:
        ctk.CTkLabel(master, text=label, anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        ctk.CTkEntry(master, textvariable=root_variable).grid(row=row, column=1, padx=(16, 6), pady=6, sticky="ew")
        actions = ctk.CTkFrame(master, fg_color="transparent")
        actions.grid(row=row, column=2, padx=(6, 16), pady=6, sticky="e")
        ctk.CTkButton(actions, text="Select", width=70, command=lambda: _select_folder(root_variable)).pack(side="left", padx=2)
        ctk.CTkButton(
            actions,
            text="Open",
            width=65,
            command=lambda: _open_profile_folder(root_variable, profile_variable),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            actions,
            text="Reset",
            width=65,
            command=lambda: _reset_profile(root_variable, profile_variable),
        ).pack(side="left", padx=2)

    @staticmethod
    def _option(master: Any, row: int, label: str, variable: tk.Variable, values: list[str]) -> None:
        ctk.CTkLabel(master, text=label, anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        ctk.CTkOptionMenu(master, variable=variable, values=values).grid(row=row, column=1, columnspan=2, padx=16, pady=6, sticky="ew")

    @staticmethod
    def _switch(master: Any, row: int, label: str, variable: tk.Variable) -> None:
        ctk.CTkSwitch(master, text=label, variable=variable).grid(row=row, column=0, columnspan=3, padx=16, pady=6, sticky="w")

    @staticmethod
    def _checkbox(master: Any, row: int, label: str, variable: tk.Variable, editable: bool) -> None:
        checkbox = ctk.CTkCheckBox(master, text=label, variable=variable)
        checkbox.grid(row=row, column=0, columnspan=3, padx=16, pady=6, sticky="w")
        if not editable:
            checkbox.configure(state="disabled")


class LogsPage(ctk.CTkFrame):
    """Live structured log viewer."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Logs", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.textbox = ctk.CTkTextbox(self, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1, wrap="none")
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self.textbox.configure(state="disabled")

    def append(self, line: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", line + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")


class AboutPage(ctk.CTkFrame):
    """Application and project information page."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color=theme.CARD, border_color=theme.BORDER, border_width=1)
        ctk.CTkLabel(self, text="ContextVault", font=ctk.CTkFont(size=30, weight="bold")).pack(pady=(80, 8))
        ctk.CTkLabel(self, text="Preserve AI Context. Forever.", text_color=theme.MUTED, font=ctk.CTkFont(size=16)).pack(pady=4)
        ctk.CTkLabel(self, text=f"Version {APPLICATION_VERSION}\nOpen-source project by Vib Tools\nhttps://vib.tools/", justify="center").pack(pady=20)


def _select_folder(variable: tk.Variable) -> None:
    selected = filedialog.askdirectory()
    if selected:
        variable.set(selected)


def _open_profile_folder(root_variable: tk.Variable, profile_variable: tk.Variable) -> None:
    root_value = str(root_variable.get()).strip()
    if not root_value:
        messagebox.showwarning("Chrome Profile", "Select the Chrome user-data folder first.")
        return
    profile_value = str(profile_variable.get()).strip() or "Default"
    profile_path = Path(root_value).expanduser() / profile_value
    target = profile_path if profile_path.is_dir() else Path(root_value).expanduser()
    if not open_path(target):
        messagebox.showerror("Chrome Profile", f"Profile folder does not exist: {target}")


def _reset_profile(root_variable: tk.Variable, profile_variable: tk.Variable) -> None:
    root_variable.set("")
    profile_variable.set("Default")


def _preview_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return text if len(text) <= 500 else f"{text[:497]}…"


def _format_size(value: int | None) -> str:
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"
