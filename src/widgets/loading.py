"""Loading spinner widget for async operations."""

from textual.widgets import Static


class LoadingSpinner(Static):
    """
    Animated loading spinner widget.

    Displays a rotating spinner animation to indicate loading or processing.
    The spinner cycles through 4 frames (◐ ◓ ◑ ◒) at 0.5 second intervals.

    Attributes:
        frames: List of Unicode characters used for animation frames
        frame_index: Current frame index in the animation cycle
        is_animating: Whether the spinner is currently animating
    """

    frames: list[str] = ["◐", "◓", "◑", "◒"]

    def __init__(
        self,
        text: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        visible: bool = True,
    ) -> None:
        """
        Initialize loading spinner.

        Args:
            text: Optional text to display alongside spinner
            name: Optional name for the widget
            id: Optional ID for the widget
            classes: Optional CSS classes
            visible: Whether the spinner is initially visible
        """
        self.frame_index: int = 0
        self.is_animating: bool = False
        initial_text = self.frames[0] + (" " + text if text else "")
        super().__init__(initial_text, name=name, id=id, classes=classes)
        self.visible = visible

    def on_mount(self) -> None:
        """Start animation when widget is mounted."""
        self.is_animating = True
        self.set_interval(0.5, self.advance_frame)

    def on_unmount(self) -> None:
        """Stop animation when widget is unmounted."""
        self.is_animating = False

    def advance_frame(self) -> None:
        """
        Advance to next animation frame.

        Cycles through the frames list and updates the display.
        Does nothing if animation is stopped.
        """
        if not self.is_animating:
            return

        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.update(self.frames[self.frame_index])

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.is_animating = False
