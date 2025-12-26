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

            # Create progress callback wrapper that updates UI directly
            def progress_callback_wrapper(progress_data: dict) -> None:
                """Wrapper to update UI with progress."""
                logger.debug(
                    f"Progress callback wrapper called: {progress_data.get('current_file', 'N/A')}"
                )
                # Update UI directly - we're already in the async main thread
                # No need for message passing since download_worker runs via run_worker()
                self.update_progress(progress_data)

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

            # Progress label with percentage
            progress_label = self.query_one("#progress-label", Label)
            downloaded = format_size(progress_data.get("overall_downloaded", 0))
            total = format_size(progress_data.get("overall_total", 0))
            file_idx = progress_data.get("current_file_index", 0)
            total_files = progress_data.get("total_files", 0)

            # Current file progress (needed for file count calculation)
            file_pct = (
                progress_data.get("current_file_downloaded", 0)
                / max(progress_data.get("current_file_total", 1), 1)
                * 100
            )

            # Calculate files actually completed (not currently downloading)
            files_completed = file_idx - 1 if file_pct < 100 else file_idx
            if progress_data.get("completed", False):
                files_completed = total_files

            # Show percentage prominently
            overall_pct_int = int(overall_pct)
            progress_label.update(
                f"{downloaded} / {total} ({overall_pct_int}%) - ({files_completed}/{total_files} files)"
            )

            # Current file
            current_file = progress_data.get("current_file", "")
            file_label = self.query_one("#file-label", Label)
            file_label.update(f"Current: {current_file}")

            # File progress bar
            file_bar = self.query_one("#file-progress", ProgressBar)
            file_bar.update(progress=file_pct)

            # Speed with color coding
            speed = progress_data.get("speed", 0)
            speed_label = self.query_one("#speed-label", Label)

            # Color-code speed based on performance
            if speed > 10 * 1024 * 1024:  # > 10 MB/s
                speed_text = f"[green]Speed: {format_speed(speed)}[/]"
            elif speed > 1 * 1024 * 1024:  # > 1 MB/s
                speed_text = f"[cyan]Speed: {format_speed(speed)}[/]"
            elif speed > 100 * 1024:  # > 100 KB/s
                speed_text = f"[yellow]Speed: {format_speed(speed)}[/]"
            elif speed > 0:  # Slow
                speed_text = f"[red]Speed: {format_speed(speed)}[/]"
            else:  # Stalled
                speed_text = f"[red]Speed: Stalled[/]"

            speed_label.update(speed_text)

            # ETA with smart stall detection
            eta = progress_data.get("eta", 0)
            eta_label = self.query_one("#eta-label", Label)

            # Calculate elapsed time for stall detection
            elapsed = 0
            if self._download_start_time:
                import time

                elapsed = time.time() - self._download_start_time

            # Show appropriate ETA based on download state
            if speed < 1024 and elapsed > 5:  # Less than 1 KB/s after 5 seconds
                eta_label.update("ETA: Download stalled")
            elif eta > 0 and speed > 0:
                eta_label.update(f"ETA: {format_time(eta)}")
            elif elapsed < 3:
                eta_label.update("ETA: Calculating...")
            else:
                eta_label.update("ETA: Unknown")

            # Elapsed time
            if self._download_start_time:
                import time

                elapsed = time.time() - self._download_start_time
                elapsed_label = self.query_one("#elapsed-label", Label)
                elapsed_label.update(f"Elapsed: {format_time(int(elapsed))}")

            # Update status with resumed download indicator
            status_label = self.query_one("#status-label", Label)
            status = progress_data.get("status", "downloading")

            # Show "Resuming" if we have initial bytes
            if status == "resuming":
                initial_bytes = progress_data.get("initial_bytes", 0)
                if initial_bytes > 0:
                    status_label.update(
                        f"Resuming download... ({format_size(initial_bytes)} already downloaded)"
                    )
                else:
                    status_label.update("Downloading...")
            elif status == "downloading":
                status_label.update("Downloading...")
            else:
                status_label.update(status)
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
