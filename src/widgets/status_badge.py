"""Status badge widget for displaying status with icons."""

from typing import Literal

from textual.widgets import Static

StatusType = Literal["success", "warning", "error", "info", "checking"]


class StatusBadge(Static):
    """
    Displays status with icon and colored badge.

    A widget that shows various status states with appropriate icons and colors.
    Supports success (✓), warning (⬆), error (✗), info (ℹ), and checking (◌) states.

    Attributes:
        ICONS: Mapping of status types to their Rich-formatted icon strings
        STATUS_TITLES: Mapping of status types to human-readable titles
    """

    ICONS: dict[StatusType, str] = {
        "success": "[green]✓[/green]",
        "warning": "[yellow]⬆[/yellow]",
        "error": "[red]✗[/red]",
        "info": "[cyan]ℹ[/cyan]",
        "checking": "[cyan]◌[/cyan]",
    }

    STATUS_TITLES: dict[StatusType, str] = {
        "success": "Up to date",
        "warning": "Update available",
        "error": "Error",
        "info": "Info",
        "checking": "Checking...",
    }

    def __init__(
        self,
        status: StatusType,
        show_text: bool = True,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize status badge.

        Args:
            status: Status type to display
            show_text: Whether to show descriptive text along with icon
            name: Optional name for the widget
            id: Optional ID for the widget
            classes: Optional additional CSS classes
        """
        if show_text:
            text = f"{self.ICONS[status]} {self.STATUS_TITLES[status]}"
        else:
            text = self.ICONS[status]

        badge_classes = f"badge badge-{status}"
        if classes:
            badge_classes = f"{badge_classes} {classes}"

        super().__init__(text, name=name, id=id, classes=badge_classes)

    def update_status(self, status: StatusType, show_text: bool = True) -> None:
        """
        Update the status of the badge.

        Args:
            status: New status value
            show_text: Whether to show descriptive text
        """
        if show_text:
            text = f"{self.ICONS[status]} {self.STATUS_TITLES[status]}"
        else:
            text = self.ICONS[status]

        self.update(text)
        self.remove_class(
            "badge-success",
            "badge-warning",
            "badge-error",
            "badge-info",
            "badge-checking",
        )
        self.add_class(f"badge-{status}")
