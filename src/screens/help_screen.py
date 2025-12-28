"""Help screen with keyboard shortcuts reference."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static, Label
from textual.binding import Binding

from src.widgets.section_header import SectionHeader


class HelpScreen(Screen):
    """Screen displaying keyboard shortcuts and help information."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("?", "close", "Close"),
    ]

    # Keyboard shortcuts organized by context
    SHORTCUTS = {
        "Global": [
            ("s", "Open search"),
            ("r", "Refresh model list"),
            ("?", "Show this help"),
            ("q", "Quit application"),
        ],
        "Main Screen": [
            ("Enter", "View model details"),
            ("d", "Delete selected model"),
            ("u", "Update selected model"),
            ("Up/Down", "Navigate model list"),
        ],
        "Search Screen": [
            ("Enter", "Select model"),
            ("Down", "Jump to results from search"),
            ("Up", "Return to search from results"),
            ("Escape", "Go back"),
        ],
        "Detail Screen": [
            ("Enter/d", "Download selected quantization"),
            ("Up/Down", "Navigate quantizations"),
            ("Escape", "Go back"),
        ],
        "Download Screen": [
            ("Escape/c", "Cancel download"),
        ],
    }

    def compose(self) -> ComposeResult:
        """Compose the help screen layout."""
        yield Header()

        with VerticalScroll():
            with Container(classes="help-container"):
                yield SectionHeader("Keyboard Shortcuts")

                for section, shortcuts in self.SHORTCUTS.items():
                    yield Static(f"[bold cyan]{section}[/]", classes="help-section-title")

                    for key, description in shortcuts:
                        yield Static(
                            f"  [green]{key:12}[/]  {description}",
                            classes="help-shortcut",
                        )

                    yield Static("")  # Spacer

                yield SectionHeader("Tips")
                yield Static(
                    "[dim]• Use Tab to switch between widgets\n"
                    "• Arrow keys navigate within tables\n"
                    "• Enter selects the current item\n"
                    "• Escape typically goes back[/]",
                    classes="help-tips",
                )

                yield Static("")
                yield Label(
                    "[dim]Press Escape, q, or ? to close this help screen[/]",
                    classes="help-footer",
                )

    def action_close(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
