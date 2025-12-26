"""Main dashboard screen."""

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, DataTable, Label
from textual.binding import Binding

from src.utils.helpers import format_size
from src.widgets.section_header import SectionHeader
from src.widgets.modal import Modal
from src.exceptions import ModelManagerException


class MainScreen(Screen):
    """Main dashboard showing downloaded models."""

    BINDINGS = [
        Binding("s", "search", "Search"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select_model", "Details"),
        Binding("d", "delete_model", "Delete"),
        Binding("u", "update_model", "Update"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        yield Header()

        with Container():
            yield SectionHeader("Downloaded Models")
            yield DataTable(id="model-table", classes="model-list")

            with Horizontal(id="status-bar"):
                yield Label("", id="storage-info")
                yield Label("", id="model-count")

    def on_mount(self) -> None:
        """Handle screen mount."""
        self._setup_table_columns()
        self.refresh_table()
        self.update_status_bar()

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize for responsive columns."""
        self._setup_table_columns()
        self.refresh_table()

    def _setup_table_columns(self) -> None:
        """Setup table columns based on terminal width."""
        table = self.query_one("#model-table", DataTable)
        width = self.app.size.width

        # Clear existing columns
        table.clear(columns=True)

        # Add columns based on available width with minimum widths for readability
        if width >= 80:
            # Desktop: All columns with proper widths
            table.add_column("Model", width=45)
            table.add_column("Files", width=12)
            table.add_column("Size", width=12)
            table.add_column("Status", width=15)
        elif width >= 60:
            # Tablet: Skip Files column
            table.add_column("Model", width=35)
            table.add_column("Size", width=12)
            table.add_column("Status", width=15)
        else:
            # Mobile: Essential only
            table.add_column("Model", width=30)
            table.add_column("Status", width=15)

        table.cursor_type = "row"

    def refresh_table(self):
        """Refresh the model table."""
        table = self.query_one("#model-table", DataTable)
        table.clear()

        app = self.app
        models = app.local_models
        width = self.app.size.width

        if not models:
            # Adapt empty row to current column count
            if width >= 80:
                table.add_row("No models downloaded", "", "", "")
            elif width >= 60:
                table.add_row("No models downloaded", "", "")
            else:
                table.add_row("No models downloaded", "")
            return

        for model in models:
            repo_id = model["repo_id"]
            file_count = len(model.get("files", []))
            size = format_size(model.get("total_size", 0))

            # Get update status
            status = app.update_statuses.get(repo_id, "unknown")
            status_display = {
                "up_to_date": "Up to date",
                "update_available": "Update available",
                "checking": "Checking...",
                "error": "Error",
                "unknown": "Unknown",
            }.get(status, status)

            # Build row conditionally based on terminal width
            if width >= 80:
                # Desktop: All columns
                table.add_row(repo_id, f"{file_count} files", size, status_display)
            elif width >= 60:
                # Tablet: Skip Files column
                table.add_row(repo_id, size, status_display)
            else:
                # Mobile: Essential only
                table.add_row(repo_id, status_display)

    def update_status_bar(self):
        """Update the status bar information."""
        app = self.app

        # Storage info
        used, total = app.storage.get_storage_usage()
        storage_label = self.query_one("#storage-info", Label)
        storage_label.update(f"Storage: {format_size(used)} / {format_size(total)}")

        # Model count
        count_label = self.query_one("#model-count", Label)
        count_label.update(f"Models: {len(app.local_models)}")

    def action_search(self) -> None:
        """Open search screen."""
        from src.screens.search_screen import SearchScreen

        self.app.push_screen(SearchScreen())

    def action_refresh(self) -> None:
        """Refresh the model list."""
        self.app.refresh_models()
        self.refresh_table()
        self.update_status_bar()
        self.app.run_worker(self.app.check_updates_async(), exclusive=True)
        self.app.notify("Refreshing model list...")

    def action_select_model(self) -> None:
        """View details of selected model."""
        table = self.query_one("#model-table", DataTable)

        if table.row_count == 0:
            return

        row_index = table.cursor_row
        if row_index >= len(self.app.local_models):
            return

        model = self.app.local_models[row_index]
        from src.screens.detail_screen import DetailScreen

        self.app.push_screen(DetailScreen(model))

    def action_delete_model(self) -> None:
        """Delete selected model."""
        table = self.query_one("#model-table", DataTable)

        if table.row_count == 0 or len(self.app.local_models) == 0:
            return

        row_index = table.cursor_row
        if row_index >= len(self.app.local_models):
            return

        model = self.app.local_models[row_index]
        repo_id = model["repo_id"]

        # Show confirmation modal
        async def handle_confirm(result: bool | None) -> None:
            if result:
                self._do_delete(repo_id)

        self.app.push_screen(
            Modal(
                title_text="Confirm Deletion", message=f"Are you sure you want to delete {repo_id}?"
            ),
            callback=handle_confirm,
        )

    def _do_delete(self, repo_id: str) -> None:
        """Handle model deletion."""
        try:
            if self.app.storage.delete_model(repo_id):
                self.app.notify(f"Deleted {repo_id}")
                self.action_refresh()
            else:
                self.app.notify(f"Failed to delete {repo_id}", severity="error")
        except ModelManagerException as e:
            self.app.notify(f"Error deleting model: {e}", severity="error")

    def action_update_model(self) -> None:
        """Update selected model."""
        table = self.query_one("#model-table", DataTable)

        if table.row_count == 0 or len(self.app.local_models) == 0:
            return

        row_index = table.cursor_row
        if row_index >= len(self.app.local_models):
            return

        model = self.app.local_models[row_index]
        repo_id = model["repo_id"]

        # Check if update is available
        status = self.app.update_statuses.get(repo_id, "unknown")
        if status != "update_available":
            self.app.notify(f"{repo_id} is already up to date")
            return

        # Get files to download
        files = model.get("files", [])
        if not files:
            self.app.notify("No files to update", severity="error")
            return

        # Start download
        from src.screens.download_screen import DownloadScreen

        self.app.push_screen(DownloadScreen(repo_id, files, is_update=True))
