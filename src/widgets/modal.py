"""Modal/Dialog widget for user confirmation."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button


class Modal(Screen):
    """
    Modal confirmation dialog with overlay.

    A modal screen that displays a yes/no confirmation dialog with a semi-transparent
    overlay. The modal blocks interaction with the underlying screen until dismissed.

    The modal returns True if user clicks "Yes", False if "No" is clicked,
    or None if dismissed via Escape key.

    Examples:
        >>> def handle_result(confirmed: bool | None) -> None:
        >>>     if confirmed:
        >>>         # User confirmed action
        >>>         pass
        >>>
        >>> modal = Modal(title_text="Delete File?", message="Are you sure?")
        >>> app.push_screen(modal, callback=handle_result)
    """

    def __init__(
        self,
        title_text: str,
        message: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize modal dialog.

        Args:
            title_text: Modal title to display at the top
            message: Main content/question to display
            name: Optional name for the screen
            id: Optional ID for the screen
            classes: Optional CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.title_text = title_text
        self.message = message

    def compose(self) -> ComposeResult:
        """
        Compose modal layout with overlay and centered dialog.

        Yields:
            Container widgets forming the modal structure
        """
        with Container(classes="modal-overlay"):
            with Container(classes="modal"):
                yield Static(self.title_text, classes="modal-title")
                yield Static(self.message)
                with Horizontal():
                    yield Button("Yes", variant="primary", id="yes-btn")
                    yield Button("No", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Dismisses the modal with True for "Yes" button, False for "No" button.

        Args:
            event: Button press event containing the clicked button
        """
        if event.button.id == "yes-btn":
            self.dismiss(True)
        elif event.button.id == "no-btn":
            self.dismiss(False)
