"""Download screen with progress tracking."""

import asyncio
import logging
from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Header, ProgressBar, Label, Button, Static
from textual.binding import Binding

from src.widgets.section_header import SectionHeader
from src.exceptions import ModelManagerException, DownloadError

logger = logging.getLogger(__name__)


class DownloadScreen(Screen):
    """Screen showing download progress with clean, professional design."""

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
        """Compose the download screen layout - clean and simple."""
        yield Header()

        with Container():
            action = "Updating" if self.is_update else "Downloading"
            yield SectionHeader(f"{action}: {self.repo_id}")

            # Simple vertical layout - no nested containers to avoid query issues
            with Vertical(classes="progress-panel"):
                # Status
                yield Label("Preparing download...", id="status-label")
                yield Static("", id="status-detail")

                # Overall Progress
                yield Static("Overall Progress", classes="section-label")
                yield Label("0 B / 0 B (0%)", id="overall-label")
                yield ProgressBar(total=100, show_eta=False, id="overall-progress")

                # Current File
                yield Static("Current File", classes="section-label")
                yield Label("Waiting...", id="file-label")
                yield ProgressBar(total=100, show_eta=False, id="file-progress")

                # Download Statistics
                yield Static("Download Statistics", classes="section-label")
                yield Label("Speed: Calculating...", id="speed-label")
                yield Label("ETA: Calculating...", id="eta-label")
                yield Label("Elapsed: 0s", id="elapsed-label")

            yield Button("Cancel", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        """Handle screen mount."""
        logger.info(f"DownloadScreen mounted: repo_id={self.repo_id}, files={len(self.files)}")

        self._is_mounted = True
        self.download_active = True
        self._download_start_time = None
        self.run_worker(self.download_worker(), exclusive=True)

    def on_unmount(self) -> None:
        """Handle screen unmount."""
        logger.info("DownloadScreen unmounting")

        self._is_mounted = False
        # Cancel download if still active
        if self.download_active:
            self.app.downloader.cancel_download()

    async def download_worker(self):
        """Worker to handle the download."""
        try:
            logger.info(f"Starting download worker for {self.repo_id}")
            app = self.app

            # Create progress callback wrapper that updates UI directly
            def progress_callback_wrapper(progress_data: dict) -> None:
                """Wrapper to update UI with progress."""
                logger.debug(f"Progress callback: {progress_data.get('current_file', 'N/A')}")
                # Update UI directly - we're already in the async main thread
                self.update_progress(progress_data)

            # Await the async download_model method
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
        except OSError as e:
            logger.error(f"System error during download: {e}", exc_info=True)
            self.download_active = False
            self.update_error(f"System error: {e}")
        except asyncio.CancelledError:
            logger.info("Download worker cancelled")
            self.download_active = False
            raise

    def update_progress(self, progress_data: dict):
        """Update progress display with comprehensive error handling."""
        from src.utils.helpers import format_size, format_speed, format_time

        # Guard against updates after unmount
        if not self._is_mounted:
            logger.debug("Skipping progress update - screen not mounted")
            return

        try:
            # === Overall Progress ===
            overall_downloaded = progress_data.get("overall_downloaded", 0)
            overall_total = progress_data.get("overall_total", 1)
            overall_pct = (overall_downloaded / max(overall_total, 1)) * 100

            # Update overall progress bar
            try:
                overall_bar = self.query_one("#overall-progress", ProgressBar)
                overall_bar.update(progress=overall_pct)
            except Exception as e:
                logger.warning(f"Failed to update overall progress bar: {e}")

            # Update overall label
            try:
                overall_label = self.query_one("#overall-label", Label)
                downloaded = format_size(overall_downloaded)
                total = format_size(overall_total)
                overall_label.update(f"{downloaded} / {total} ({int(overall_pct)}%)")
            except Exception as e:
                logger.warning(f"Failed to update overall label: {e}")

            # === Current File Progress ===
            current_file = progress_data.get("current_file", "Unknown")
            current_file_downloaded = progress_data.get("current_file_downloaded", 0)
            current_file_total = progress_data.get("current_file_total", 1)
            file_pct = (current_file_downloaded / max(current_file_total, 1)) * 100

            # Update current file label
            try:
                file_label = self.query_one("#file-label", Label)
                file_idx = progress_data.get("current_file_index", 0)
                total_files = progress_data.get("total_files", 0)
                file_label.update(f"{current_file} ({file_idx}/{total_files})")
            except Exception as e:
                logger.warning(f"Failed to update file label: {e}")

            # Update file progress bar
            try:
                file_bar = self.query_one("#file-progress", ProgressBar)
                file_bar.update(progress=file_pct)
            except Exception as e:
                logger.warning(f"Failed to update file progress bar: {e}")

            # === Download Statistics ===
            speed = progress_data.get("speed", 0)
            eta = progress_data.get("eta", 0)

            # Update speed label with color coding
            try:
                speed_label = self.query_one("#speed-label", Label)
                if speed > 10 * 1024 * 1024:  # > 10 MB/s
                    speed_text = f"[green]Speed: {format_speed(speed)}[/]"
                elif speed > 1 * 1024 * 1024:  # > 1 MB/s
                    speed_text = f"[cyan]Speed: {format_speed(speed)}[/]"
                elif speed > 100 * 1024:  # > 100 KB/s
                    speed_text = f"[yellow]Speed: {format_speed(speed)}[/]"
                elif speed > 0:  # Slow
                    speed_text = f"[red]Speed: {format_speed(speed)}[/]"
                else:  # Stalled
                    speed_text = "[red]Speed: Stalled[/]"
                speed_label.update(speed_text)
            except Exception as e:
                logger.warning(f"Failed to update speed label: {e}")

            # Update ETA label
            try:
                eta_label = self.query_one("#eta-label", Label)
                if eta > 0 and speed > 0:
                    eta_label.update(f"ETA: {format_time(eta)}")
                elif speed > 0:
                    eta_label.update("ETA: Calculating...")
                else:
                    eta_label.update("ETA: Unknown")
            except Exception as e:
                logger.warning(f"Failed to update ETA label: {e}")

            # Update elapsed time
            try:
                if self._download_start_time:
                    import time

                    elapsed = time.time() - self._download_start_time
                    elapsed_label = self.query_one("#elapsed-label", Label)
                    elapsed_label.update(f"Elapsed: {format_time(int(elapsed))}")
            except Exception as e:
                logger.warning(f"Failed to update elapsed label: {e}")

            # === Status Update ===
            try:
                status_label = self.query_one("#status-label", Label)
                status = progress_data.get("status", "downloading")

                if status == "resuming":
                    initial_bytes = progress_data.get("initial_bytes", 0)
                    if initial_bytes > 0:
                        status_label.update(
                            f"[cyan]Resuming download "
                            f"({format_size(initial_bytes)} already downloaded)[/]"
                        )
                    else:
                        status_label.update("[green]Downloading...[/]")
                elif status == "downloading":
                    status_label.update("[green]Downloading...[/]")
                else:
                    status_label.update(f"[cyan]{status}[/]")
            except Exception as e:
                logger.warning(f"Failed to update status label: {e}")

        except Exception as e:
            logger.error(f"Error updating progress UI: {e}", exc_info=True)

    def update_completion(self):
        """Update display on completion."""
        # Guard against updates after unmount
        if not self._is_mounted:
            return

        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update("[green]Download completed successfully![/]")

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
            logger.error(f"Error in update_completion: {e}", exc_info=True)

    def update_error(self, message: str | None = None):
        """Update display on error."""
        # Guard against updates after unmount
        if not self._is_mounted:
            return

        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update("[red]Download failed![/]")

            cancel_btn = self.query_one("#cancel-btn", Button)
            cancel_btn.label = "Close"
            cancel_btn.variant = "error"

            error_msg = message or "Download failed. Check logs for details."
            self.app.notify(error_msg, severity="error")
        except Exception as e:
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
