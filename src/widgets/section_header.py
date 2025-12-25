"""Section header widget with consistent styling."""

from textual.widgets import Static


class SectionHeader(Static):
    """
    Styled section header widget.

    Displays a formatted section header with optional icon prefix.
    Automatically applies 'section-header' CSS class for consistent styling.

    Examples:
        >>> SectionHeader("Downloaded Models")
        >>> SectionHeader("Search Results", icon="🔍")
    """

    def __init__(
        self,
        title: str,
        icon: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize section header.

        Args:
            title: Section title text to display
            icon: Optional icon/emoji to display before title
            name: Optional name for the widget
            id: Optional ID for the widget
            classes: Optional additional CSS classes
        """
        if icon:
            text = f"{icon} {title}"
        else:
            text = title

        header_classes = "section-header"
        if classes:
            header_classes = f"{header_classes} {classes}"

        super().__init__(text, name=name, id=id, classes=header_classes)
