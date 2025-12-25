"""Styled button widget with variants."""

from typing import Literal

from textual.widgets import Button

ButtonVariant = Literal["default", "primary", "error"]


class StyledButton(Button):
    """
    Button widget with style variants.

    Extends Textual's Button with predefined style variants for consistent UI.
    Supports default, primary (highlighted), and error (warning) styles.

    Attributes:
        VALID_VARIANTS: Set of valid variant names
    """

    VALID_VARIANTS: set[ButtonVariant] = {"default", "primary", "error"}

    def __init__(
        self,
        label: str,
        variant: ButtonVariant = "default",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """
        Initialize styled button.

        Args:
            label: Button text to display
            variant: Button style variant
            name: Optional name for the widget
            id: Optional ID for the widget
            classes: Optional additional CSS classes
            disabled: Whether the button is initially disabled

        Raises:
            ValueError: If variant is not in VALID_VARIANTS
        """
        if variant not in self.VALID_VARIANTS:
            raise ValueError(
                f"Invalid variant '{variant}'. Must be one of {self.VALID_VARIANTS}"
            )

        super().__init__(label, name=name, id=id, classes=classes, disabled=disabled)

        if variant != "default":
            self.add_class(f"-{variant}")
