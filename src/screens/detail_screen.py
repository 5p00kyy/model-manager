"""Model detail screen."""

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Header, Static, Button, Label, DataTable
from textual.binding import Binding

from src.widgets.section_header import SectionHeader
from src.widgets.modal import Modal
from src.widgets.loading import LoadingSpinner
from src.exceptions import HuggingFaceError


class DetailScreen(Screen):
    """Screen showing detailed model information."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("d", "download", "Download Selected"),
        Binding("enter", "download", "Download", show=False),
    ]

    def __init__(self, model_data: dict, is_remote: bool = False):
        super().__init__()
        self.model_data = model_data
        self.is_remote = is_remote
        self.quant_groups = []

    def compose(self) -> ComposeResult:
        """Compose the detail screen layout."""
        yield Header()

        with ScrollableContainer():
            with Container():
                repo_id = self.model_data.get("repo_id", "")
                yield SectionHeader(repo_id)

                # Model info
                with Vertical(id="model-info", classes="info-panel"):
                    if self.is_remote:
                        downloads = self.model_data.get("downloads", 0)
                        likes = self.model_data.get("likes", 0)
                        yield Label(f"Downloads: {downloads:,}")
                        yield Label(f"Likes: {likes}")

                        description = self.model_data.get("description", "No description available")
                        yield Label(f"Description: {description}")

                        tags = self.model_data.get("tags", [])
                        if tags:
                            yield Label(f"Tags: {', '.join(tags[:10])}")
                    else:
                        # Local model
                        files = self.model_data.get("files", [])
                        yield Label(f"Files: {len(files)}")

                        from src.utils.helpers import format_size

                        size = format_size(self.model_data.get("total_size", 0))
                        yield Label(f"Total Size: {size}")

                        download_date = self.model_data.get("download_date", "Unknown")
                        yield Label(f"Downloaded: {download_date}")

                # Available quantizations (for remote models)
                if self.is_remote:
                    yield SectionHeader("Available Quantizations")
                    with Horizontal():
                        yield DataTable(id="quant-table", classes="model-list")
                        yield LoadingSpinner(id="quant-spinner", visible=False)
                    yield Static("Loading quantizations...", id="quant-status")

                # Action buttons
                with Horizontal():
                    if self.is_remote:
                        yield Button("Download Selected", variant="primary", id="download-btn")
                    yield Button("Back", variant="default", id="back-btn")

    def on_mount(self) -> None:
        """Handle screen mount."""
        if self.is_remote:
            # Load quantizations
            self.run_worker(self.load_quants_worker(), exclusive=True)

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize for responsive layout."""
        if self.is_remote and self.quant_groups:
            self.update_quant_table()

    async def load_quants_worker(self):
        """Load quantization groups."""
        repo_id = self.model_data["repo_id"]
        app = self.app

        spinner = None
        try:
            # Get spinner widget
            spinner = self.query_one("#quant-spinner", LoadingSpinner)
            status = self.query_one("#quant-status", Static)

            spinner.visible = True
            status.update("Loading quantizations...")

            # Get GGUF files
            gguf_files = app.hf_client.list_gguf_files(repo_id)

            if not gguf_files:
                status.update("No GGUF files found")
                return

            # Group files
            from src.utils.helpers import group_multipart_files

            grouped = group_multipart_files(gguf_files)

            # Get file sizes with error handling
            try:
                file_sizes = app.hf_client.get_file_sizes(repo_id)
                if not file_sizes:
                    self.app.notify(
                        "Could not fetch file sizes - sizes may show as 0", severity="warning"
                    )
                    file_sizes = {}
            except Exception as size_error:
                self.app.notify(f"Error fetching file sizes: {size_error}", severity="warning")
                file_sizes = {}

            self.quant_groups = []
            all_sizes_zero = True

            for name, files in grouped.items():
                total_size = sum(file_sizes.get(f, 0) for f in files)
                if total_size > 0:
                    all_sizes_zero = False
                self.quant_groups.append({"name": name, "files": files, "total_size": total_size})

            # Warn if all sizes are zero
            if all_sizes_zero and file_sizes:
                self.app.notify(
                    "File sizes unavailable from API - download will proceed but size is unknown",
                    severity="warning",
                )

            # Update table
            self.update_quant_table()

            # Auto-focus table for seamless navigation (no Tab needed!)
            self.call_after_refresh(self._focus_quant_table)

        except HuggingFaceError as e:
            status = self.query_one("#quant-status", Static)
            status.update(f"Error: {e}")
            self.app.notify(f"Failed to load quantizations: {e}", severity="error")
        except Exception as e:
            status = self.query_one("#quant-status", Static)
            status.update(f"Error: {e}")
            self.app.notify(f"Failed to load quantizations: {e}", severity="error")
        finally:
            if spinner:
                spinner.visible = False

    def update_quant_table(self):
        """Update the quantization table."""
        from src.utils.helpers import format_size

        table = self.query_one("#quant-table", DataTable)
        status = self.query_one("#quant-status", Static)
        width = self.app.size.width

        # Clear and rebuild columns
        table.clear(columns=True)

        # Add columns based on terminal width with minimum widths
        if width >= 60:
            # Desktop/Tablet: All columns with proper widths
            table.add_column("Quantization", width=25)
            table.add_column("Files", width=15)
            table.add_column("Size", width=15)
        else:
            # Mobile: Essential columns only
            table.add_column("Quantization", width=25)
            table.add_column("Size", width=15)

        table.cursor_type = "row"

        if not self.quant_groups:
            status.update("No quantizations available")
            return

        status.update(f"{len(self.quant_groups)} quantizations available")

        for quant in self.quant_groups:
            name = quant["name"]
            file_count = len(quant["files"])
            size = format_size(quant["total_size"])

            # Build row conditionally based on terminal width
            if width >= 60:
                table.add_row(name, f"{file_count} file(s)", size)
            else:
                table.add_row(name, size)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "download-btn":
            self.action_download()
        elif event.button.id == "back-btn":
            self.action_back()

    def action_download(self) -> None:
        """Start download with validation."""
        if not self.is_remote:
            return

        if not self.quant_groups:
            self.app.notify("No quantizations available", severity="error")
            return

        table = self.query_one("#quant-table", DataTable)
        row_index = table.cursor_row

        if row_index >= len(self.quant_groups):
            return

        quant = self.quant_groups[row_index]
        repo_id = self.model_data["repo_id"]
        files = quant["files"]
        total_size = quant["total_size"]

        from src.utils.helpers import format_size

        size_str = format_size(total_size) if total_size > 0 else "Unknown size"

        # Show confirmation modal with validation
        async def handle_confirm(result: bool | None) -> None:
            if result:
                # Run validation before starting download
                valid, error_msg = await self.app.downloader.validate_download(
                    repo_id, files, total_size
                )

                if not valid:
                    self.app.notify(f"Cannot download: {error_msg}", severity="error")
                    return

                from src.screens.download_screen import DownloadScreen

                self.app.push_screen(DownloadScreen(repo_id, files, is_update=False))

        self.app.push_screen(
            Modal(
                title_text="Confirm Download",
                message=f"Download {quant['name']} ({size_str}) from {repo_id}?",
            ),
            callback=handle_confirm,
        )

    def action_back(self) -> None:
        """Go back."""
        self.app.pop_screen()

    def _focus_quant_table(self) -> None:
        """Focus the quantization table after loading."""
        if not self.is_remote:
            return
        try:
            table = self.query_one("#quant-table", DataTable)
            if table.row_count > 0:
                table.focus()
        except Exception:
            pass  # Table might not exist if we navigated away

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on table row - directly start download."""
        if self.is_remote:
            self.action_download()

    def on_key(self, event: events.Key) -> None:
        """Handle smart keyboard navigation between table and buttons."""
        if not self.is_remote:
            return

        try:
            table = self.query_one("#quant-table", DataTable)
            download_btn = self.query_one("#download-btn", Button)

            # DOWN arrow from Download button → jump to table
            if event.key == "down" and download_btn.has_focus:
                if table.row_count > 0:
                    table.focus()
                    event.prevent_default()

            # UP arrow at top of table → return to Download button
            elif event.key == "up" and table.has_focus:
                if table.cursor_row == 0:
                    download_btn.focus()
                    event.prevent_default()
        except Exception:
            pass  # Widgets might not exist
