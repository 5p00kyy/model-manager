"""Download screen with progress tracking."""

from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Header, ProgressBar, Label, Button
from textual.binding import Binding

from src.widgets.section_header import SectionHeader
from src.exceptions import ModelManagerException, DownloadError


class DownloadScreen(Screen):
    """Screen showing download progress."""

    class ProgressUpdate(Message):
        """Message sent when download progress updates."""

        def __init__(self, progress_data: dict) -> None:
            super().__init__()
            self.progress_data = progress_data

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("c", "cancel", "Cancel"),
    ]

    def __init__(self, repo_id: str, files: List[str], is_update: bool = False):
        super().__init__()
        self.repo_id = repo_id
        self.files = files
        self.is_update = is_update
        self.download_active = False
        self._is_mounted = False

    def compose(self) -> ComposeResult:
        """Compose the download screen layout."""
        yield Header()

        with Container():
            action = "Updating" if self.is_update else "Downloading"
            yield SectionHeader(f"{action}: {self.repo_id}")

            with Vertical(classes="progress-panel"):
                yield Label("Preparing download...", id="status-label")
                yield Label("", id="progress-label")
                yield ProgressBar(total=100, show_eta=False, id="overall-progress")

                yield Label("", id="file-label")
                yield ProgressBar(total=100, show_eta=False, id="file-progress")

                yield Label("", id="speed-label")
                yield Label("", id="eta-label")
                yield Label("", id="elapsed-label")

                yield Label("", id="file-list")

            yield Button("Cancel", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        """Handle screen mount."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"DownloadScreen mounted: repo_id={self.repo_id}, files={len(self.files)}")

        self._is_mounted = True
        self.download_active = True
        self._download_start_time = None
        self.run_worker(self.download_worker(), exclusive=True)

    def on_unmount(self) -> None:
        """Handle screen unmount."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"DownloadScreen unmounting")

        self._is_mounted = False
        # Cancel download if still active
        if self.download_active:
            self.app.downloader.cancel_download()

    async def download_worker(self):
        """Worker to handle the download."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Starting download worker for {self.repo_id}")
            app = self.app

            # Create progress callback wrapper that posts messages
            def progress_callback_wrapper(progress_data: dict) -> None:
                """Wrapper to post progress updates as messages."""
                logger.debug(
                    f"Progress callback wrapper called: {progress_data.get('current_file', 'N/A')}"
                )
                # Post message to main thread for UI update
                self.post_message(self.ProgressUpdate(progress_data))

            # Await the now-async download_model method
            logger.info("Calling download_model...")
            import time

            self._download_start_time = time.time()
            success = await app.downloader.download_model(
                self.repo_id, self.files, progress_callback=progress_callback_wrapper
            )

            logger.info(f"Download completed: success={success}")
            self.download_active = False

            if success:
                self.update_completion()
            else:
                self.update_error()
        except DownloadError as e:
            logger.error(f"DownloadError: {e}", exc_info=True)
            self.download_active = False
            self.update_error(str(e))
        except ModelManagerException as e:
            logger.error(f"ModelManagerException: {e}", exc_info=True)
            self.download_active = False
            self.update_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            self.download_active = False
            self.update_error(f"Unexpected error: {e}")

    def on_progress_update(self, message: ProgressUpdate) -> None:
        """Handle progress update messages from worker thread."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"UI UPDATE: {message.progress_data.get('current_file', 'unknown')} - {message.progress_data.get('overall_downloaded', 0)}/{message.progress_data.get('overall_total', 0)} bytes"
        )
        self.update_progress(message.progress_data)

    def update_progress(self, progress_data: dict):
        """Update progress display."""
        import logging
        from src.utils.helpers import format_size, format_speed, format_time

        logger = logging.getLogger(__name__)
        logger.debug(
            f"PROGRESS CALLBACK: {progress_data.get('current_file', 'unknown')} - {progress_data.get('overall_downloaded', 0)}/{progress_data.get('overall_total', 0)} bytes"
        )

        # Guard against updates after unmount
        if not self._is_mounted:
            logger.debug("Skipping progress update - screen not mounted")
            return

        try:
            # Overall progress
            overall_pct = (
                progress_data.get("overall_downloaded", 0)
                / max(progress_data.get("overall_total", 1), 1)
                * 100
            )
            overall_bar = self.query_one("#overall-progress", ProgressBar)
            overall_bar.update(progress=overall_pct)

            # Progress label
            progress_label = self.query_one("#progress-label", Label)
            downloaded = format_size(progress_data.get("overall_downloaded", 0))
            total = format_size(progress_data.get("overall_total", 0))
            file_idx = progress_data.get("current_file_index", 0)
            total_files = progress_data.get("total_files", 0)
            progress_label.update(f"{downloaded} / {total}  ({file_idx}/{total_files} files)")

            # Current file
            current_file = progress_data.get("current_file", "")
            file_label = self.query_one("#file-label", Label)
            file_label.update(f"Current: {current_file}")

            # File progress
            file_pct = (
                progress_data.get("current_file_downloaded", 0)
                / max(progress_data.get("current_file_total", 1), 1)
                * 100
            )
            file_bar = self.query_one("#file-progress", ProgressBar)
            file_bar.update(progress=file_pct)

            # Speed
            speed = progress_data.get("speed", 0)
            speed_label = self.query_one("#speed-label", Label)
            speed_label.update(f"Speed: {format_speed(speed)}")

            # ETA
            eta = progress_data.get("eta", 0)
            eta_label = self.query_one("#eta-label", Label)
            if eta > 0:
                eta_label.update(f"ETA: {format_time(eta)}")
            else:
                eta_label.update("ETA: Calculating...")

            # Elapsed time
            if self._download_start_time:
                import time

                elapsed = time.time() - self._download_start_time
                elapsed_label = self.query_one("#elapsed-label", Label)
                elapsed_label.update(f"Elapsed: {format_time(int(elapsed))}")

            # Update status
            status_label = self.query_one("#status-label", Label)
            status_label.update("Downloading...")
        except Exception as e:
            logger.error(f"Error updating progress UI: {e}", exc_info=True)

    def update_completion(self):
        """Update display on completion."""
        # Guard against updates after unmount
        if not self._is_mounted:
            return

        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update("Download completed!")

            overall_bar = self.query_one("#overall-progress", ProgressBar)
            overall_bar.update(progress=100)

            file_bar = self.query_one("#file-progress", ProgressBar)
            file_bar.update(progress=100)

            # Update button
            cancel_btn = self.query_one("#cancel-btn", Button)
            cancel_btn.label = "Close"
            cancel_btn.variant = "primary"

            # Notify and refresh main screen
            self.app.notify("Download completed successfully!")
            self.app.refresh_models()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in update_completion: {e}", exc_info=True)

    def update_error(self, message: str | None = None):
        """Update display on error."""
        # Guard against updates after unmount
        if not self._is_mounted:
            return

        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update("Download failed!")

            cancel_btn = self.query_one("#cancel-btn", Button)
            cancel_btn.label = "Close"
            cancel_btn.variant = "error"

            error_msg = message or "Download failed. Check logs for details."
            self.app.notify(error_msg, severity="error")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in update_error: {e}", exc_info=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if self.download_active:
            self.action_cancel()
        else:
            self.app.pop_screen()

    def action_cancel(self) -> None:
        """Cancel the download."""
        if self.download_active:
            self.app.downloader.cancel_download()
            self.app.notify("Download cancelled")
            self.download_active = False

        self.app.pop_screen()
