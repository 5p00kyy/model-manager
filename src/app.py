"""Main Textual application."""

import logging

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from src.config import MODELS_DIR, METADATA_FILE, LOG_FILE, APP_NAME, APP_VERSION
from src.theme import get_theme_css
from src.services.hf_client import HuggingFaceClient
from src.services.storage import StorageManager
from src.services.downloader import DownloadManager
from src.services.updater import UpdateChecker

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class ModelManagerApp(App):
    """Main Model Manager application."""

    CSS = get_theme_css()

    TITLE = f"{APP_NAME} v{APP_VERSION}"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "search", "Search", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        ("?", "help", "Help"),
    ]

    def on_exception(self, event):
        """Global exception handler."""
        logger.error(f"Uncaught exception: {event.exception}")
        self.notify(f"An error occurred: {event.exception}", severity="error", timeout=5)
        event.prevent_default()

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        # Initialize services
        self.hf_client = HuggingFaceClient()
        self.storage = StorageManager(MODELS_DIR, METADATA_FILE)
        self.downloader = DownloadManager(self.hf_client, self.storage)
        self.updater = UpdateChecker(self.hf_client, self.storage)

        # Application state
        self.local_models = []
        self.update_statuses = {}
        self.current_download = None
        self._resize_pending = False

        logger.info(f"{APP_NAME} v{APP_VERSION} started")

    def compose(self) -> ComposeResult:
        """Compose application layout."""
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        from src.screens.main_screen import MainScreen

        # Set initial responsive class
        self._update_responsive_class()

        self.push_screen(MainScreen())

        # Load local models
        self.refresh_models()

        # Start async update check
        self.run_worker(self.check_updates_async(), exclusive=True)

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize for responsive design with debouncing."""
        # Mark that a resize is pending
        self._resize_pending = True

        # Schedule the actual resize with 200ms delay
        # This cancels any previous pending resize
        def apply_with_flag():
            if self._resize_pending:
                self._update_responsive_class()
                self._resize_pending = False

        self.set_timer(0.2, apply_with_flag)

    def _update_responsive_class(self) -> None:
        """Update responsive CSS class based on terminal size."""
        width = self.size.width

        # Remove all size classes
        self.remove_class("mobile", "tablet", "desktop", "tiny")

        # Add appropriate class based on width
        if width < 40:
            self.add_class("tiny")
            logger.debug(f"Responsive: tiny mode ({width} cols)")
        elif width < 60:
            self.add_class("mobile")
            logger.debug(f"Responsive: mobile mode ({width} cols)")
        elif width < 80:
            self.add_class("tablet")
            logger.debug(f"Responsive: tablet mode ({width} cols)")
        else:
            self.add_class("desktop")
            logger.debug(f"Responsive: desktop mode ({width} cols)")

    def refresh_models(self):
        """Refresh the list of local models."""
        self.local_models = self.storage.scan_local_models()
        logger.info(f"Loaded {len(self.local_models)} local models")

    async def check_updates_async(self):
        """Check for updates asynchronously."""
        try:
            if not self.local_models:
                return

            logger.info(f"Checking updates for {len(self.local_models)} models")

            for model in self.local_models:
                repo_id = model["repo_id"]
                self.update_statuses[repo_id] = "checking"

                # This will be visible on the main screen
                self.refresh()

            # Check each model
            results = self.updater.check_for_updates(self.local_models)
            self.update_statuses.update(results)

            logger.info(f"Update check complete: {results}")
            self.refresh()
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            # Set all to error state
            for model in self.local_models:
                self.update_statuses[model["repo_id"]] = "error"

    def action_search(self) -> None:
        """Open search screen."""
        from src.screens.search_screen import SearchScreen

        self.push_screen(SearchScreen())

    def action_refresh(self) -> None:
        """Refresh model list."""
        self.refresh_models()
        self.run_worker(self.check_updates_async(), exclusive=True)

    def action_help(self) -> None:
        """Show help."""
        self.notify("Keyboard shortcuts: S=Search, R=Refresh, Q=Quit")


def run():
    """Run the application."""
    app = ModelManagerApp()
    app.run()
