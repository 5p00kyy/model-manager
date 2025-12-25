"""Card/Panel container widget with consistent styling."""

from textual.widgets import Static


class PanelCard(Static):
    """
    Card-style container widget.

    A container widget with consistent border, padding, and background styling.
    Provides hover effects and can be used to group related content.

    The card automatically applies background color, border, padding, and margin
    from the theme. On hover, the background lightens slightly.

    Examples:
        >>> with PanelCard():
        >>>     yield Label("Content inside card")
        >>>     yield Button("Action")
    """

    DEFAULT_CSS = """
    PanelCard {
        background: $surface;
        border: solid $border;
        padding: 2;
        margin: 1;
    }

    PanelCard:hover {
        background: $surface-hover;
    }
    """

    def __init__(
        self,
        *children,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize panel card container.

        Args:
            *children: Child widgets to add to the card
            name: Optional name for the widget
            id: Optional ID for the widget
            classes: Optional additional CSS classes
        """
        super().__init__(*children, name=name, id=id, classes=classes)
