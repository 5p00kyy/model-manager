"""Search screen for finding models."""

import asyncio

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Input, Static, DataTable
from textual.binding import Binding

from src.widgets.loading import LoadingSpinner
from src.widgets.section_header import SectionHeader
from src.exceptions import HuggingFaceError


class SearchScreen(Screen):
    """Screen for searching HuggingFace models."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("enter", "select_model", "Select"),
        Binding("q", "go_back", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.search_results = []
        self.debounce_timer = None

    def compose(self) -> ComposeResult:
        """Compose the search screen layout."""
        yield Header()

        with Container():
            yield SectionHeader("Search GGUF Models")
            yield Input(
                placeholder="Enter search keywords (e.g., 'llama', 'mistral')...", id="search-input"
            )
            with Horizontal():
                yield Static("", id="result-count")
                yield LoadingSpinner(id="search-spinner", visible=False)
            yield DataTable(id="results-table", classes="model-list")

    def on_mount(self) -> None:
        """Handle screen mount."""
        self._setup_table_columns()

        # Focus on search input
        self.query_one("#search-input", Input).focus()

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize for responsive columns."""
        self._setup_table_columns()
        self.update_results()

    def _setup_table_columns(self) -> None:
        """Setup table columns based on terminal width."""
        table = self.query_one("#results-table", DataTable)
        width = self.app.size.width

        # Clear existing columns
        table.clear(columns=True)

        # Add columns based on available width with minimum widths for readability
        if width >= 80:
            # Desktop: All columns with proper widths
            table.add_column("Model", width=35)
            table.add_column("Author", width=20)
            table.add_column("Downloads", width=15)
            table.add_column("Description", width=None)  # Flexible width
        elif width >= 60:
            # Tablet: Skip Description
            table.add_column("Model", width=30)
            table.add_column("Author", width=18)
            table.add_column("Downloads", width=15)
        else:
            # Mobile: Essential only
            table.add_column("Model", width=30)
            table.add_column("Downloads", width=15)

        table.cursor_type = "row"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()

        if not query:
            self.clear_results()
            return

        # Debounce search
        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = asyncio.create_task(self.debounced_search(query))

    async def debounced_search(self, query: str):
        """Search with debouncing."""
        await asyncio.sleep(0.5)  # Wait 500ms
        await self.perform_search(query)

    async def perform_search(self, query: str):
        """Perform the actual search."""
        count_label = self.query_one("#result-count", Static)
        spinner = self.query_one("#search-spinner", LoadingSpinner)
        count_label.update("Searching...")
        spinner.visible = True

        # Run search in worker
        self.run_worker(self.search_worker(query), exclusive=True)

    async def search_worker(self, query: str):
        """Worker to search for models."""
        try:
            app = self.app
            results = app.hf_client.search_models(query, limit=50)

            self.search_results = results
            self.update_results()
        except HuggingFaceError as e:
            self.app.notify(f"Search failed: {e}", severity="error")
            self.update_results_error()
        except Exception as e:
            self.app.notify(f"Unexpected error: {e}", severity="error")
            self.update_results_error()
        finally:
            spinner = self.query_one("#search-spinner", LoadingSpinner)
            spinner.visible = False

    def update_results_error(self):
        """Update results on error."""
        table = self.query_one("#results-table", DataTable)
        count_label = self.query_one("#result-count", Static)

        table.clear()
        count_label.update("Search failed")

    def update_results(self):
        """Update the results table."""
        table = self.query_one("#results-table", DataTable)
        count_label = self.query_one("#result-count", Static)
        width = self.app.size.width

        table.clear()

        if not self.search_results:
            count_label.update("No results found")
            return

        count_label.update(f"Found {len(self.search_results)} models (↓ to navigate)")

        for model in self.search_results:
            repo_id = model["repo_id"]
            author = model.get("author", "")
            downloads = model.get("downloads", 0)
            description = model.get("description", "")[:50]  # Truncate

            # Format downloads
            if downloads > 1000000:
                downloads_str = f"{downloads/1000000:.1f}M"
            elif downloads > 1000:
                downloads_str = f"{downloads/1000:.1f}K"
            else:
                downloads_str = str(downloads)

            # Build row conditionally based on terminal width
            if width >= 80:
                # Desktop: All columns
                table.add_row(repo_id, author, downloads_str, description)
            elif width >= 60:
                # Tablet: Skip Description
                table.add_row(repo_id, author, downloads_str)
            else:
                # Mobile: Essential only
                table.add_row(repo_id, downloads_str)

        # Auto-focus table after results load for immediate navigation
        self.call_after_refresh(self._focus_table)

    def clear_results(self):
        """Clear search results."""
        table = self.query_one("#results-table", DataTable)
        count_label = self.query_one("#result-count", Static)

        table.clear()
        count_label.update("")
        self.search_results = []

    def action_select_model(self) -> None:
        """Select a model from search results."""
        table = self.query_one("#results-table", DataTable)

        if table.row_count == 0 or not self.search_results:
            return

        row_index = table.cursor_row
        if row_index >= len(self.search_results):
            return

        model_data = self.search_results[row_index]

        # Open detail screen for this model
        from src.screens.detail_screen import DetailScreen

        self.app.push_screen(DetailScreen(model_data, is_remote=True))

    def _focus_table(self) -> None:
        """Focus the results table after refresh."""
        table = self.query_one("#results-table", DataTable)
        if table.row_count > 0:
            table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key or double-click on table row."""
        self.action_select_model()

    def on_key(self, event: events.Key) -> None:
        """Handle special keyboard navigation."""
        table = self.query_one("#results-table", DataTable)
        search_input = self.query_one("#search-input", Input)

        # DOWN arrow from search input → jump to table
        if event.key == "down" and search_input.has_focus:
            if table.row_count > 0:
                table.focus()
                event.prevent_default()

        # UP arrow at top of table → return to search
        elif event.key == "up" and table.has_focus:
            if table.cursor_row == 0:
                search_input.focus()
                event.prevent_default()

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
