"""Theme configuration and color palette for Model Manager."""

DARK_THEME = {
    "background": "#0d1117",
    "surface": "#161b22",
    "surface-hover": "#1c2128",
    "primary": "#3fb950",  # Changed from blue to vibrant green
    "primary-dim": "#2ea043",  # Darker green
    "primary-bright": "#56d364",  # Lighter green
    "accent": "#a371f7",
    "accent-dim": "#8957e5",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "info": "#3fb950",  # Changed from blue to green
    "text-primary": "#e6edf3",
    "text-secondary": "#7d8590",
    "text-muted": "#484f58",
    "border": "#30363d",
    "border-focus": "#3fb950",  # Changed from blue to green
    "selection": "#2ea04340",  # Green with transparency
}


DARK_THEME_CSS = """
/* ===== Color Variables ===== */
$background: #0d1117;
$surface: #161b22;
$surface-hover: #1c2128;
$primary: #3fb950;
$primary-dim: #2ea043;
$primary-bright: #56d364;
$accent: #a371f7;
$accent-dim: #8957e5;
$success: #3fb950;
$warning: #d29922;
$error: #f85149;
$info: #3fb950;
$text-primary: #e6edf3;
$text-secondary: #7d8590;
$text-muted: #484f58;
$border: #30363d;
$border-focus: #3fb950;
$selection: rgba(46, 160, 67, 0.25);

/* ===== Spacing ===== */
$spacing-xs: 1;
$spacing-sm: 2;
$spacing-md: 4;
$spacing-lg: 6;
$spacing-xl: 8;

/* ===== Base Styles ===== */
Screen {
    background: $background;
    color: $text-primary;
}

/* ===== Header & Footer ===== */
Header {
    background: $surface;
    color: $primary-bright;
    padding: 1 2;
    border-bottom: solid $border;
    text-style: bold;
}

Footer {
    background: $surface;
    color: $text-secondary;
    border-top: solid $border;
}

/* ===== Cards & Panels ===== */
.card {
    background: $surface;
    border: solid $border;
    padding: 2;
    margin: 1;
}

.card:hover {
    background: $surface-hover;
}

.panel {
    background: $surface;
    border: thick $primary-dim;
    padding: 2;
}

/* ===== Section Headers ===== */
.section-header {
    background: $surface;
    color: $primary-bright;
    text-style: bold;
    border-bottom: solid $primary-dim;
    padding: 1 2;
    margin-bottom: 1;
}

.section-label {
    color: $primary-bright;
    text-style: bold;
    margin-top: 1;
}

/* ===== DataTable ===== */
DataTable {
    background: $surface;
    color: $text-primary;
    min-width: 40;  /* Minimum width to prevent squishing */
    width: 100%;    /* Use full available width */
}

DataTable > .datatable--header {
    background: $surface;
    color: $primary-bright;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $selection;
    color: $text-primary;
}

DataTable:focus > .datatable--cursor {
    background: $primary-dim;
    color: $text-primary;
}

DataTable > .datatable--hover {
    background: $surface-hover;
}

/* Ensure table columns don't overflow */
DataTable .datatable--cell {
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ===== Input ===== */
Input {
    background: $surface;
    border: solid $border;
    color: $text-primary;
}

Input:focus {
    border: solid $border-focus;
}

/* ===== Buttons ===== */
Button {
    background: $surface;
    border: solid $border;
    color: $text-primary;
}

Button:hover {
    background: $surface-hover;
}

Button.-primary {
    background: $primary;
    color: $background;
    border: none;
}

Button.-primary:hover {
    background: $primary-bright;
}

Button.-error {
    background: $error;
    color: $background;
    border: none;
}

/* ===== Progress Bar ===== */
ProgressBar {
    background: $surface;
    color: $primary;
    height: 1;
}

ProgressBar > .bar--bar {
    color: $primary;
    text-style: bold;
}

ProgressBar > .bar--complete {
    color: $success;
    text-style: bold;
}

/* Enhanced progress bar for overall progress */
#overall-progress {
    height: 2;
    border: solid $primary-dim;
    background: $surface;
}

#overall-progress > .bar--bar {
    color: $primary-bright;
    text-style: bold;
}

/* File progress bar */
#file-progress {
    height: 1;
    background: $surface-hover;
}

/* Progress panel container */
.progress-panel {
    background: $surface;
    border: thick $border;
    padding: 2;
    margin: 1;
}

/* Progress containers for better hierarchy */
.progress-main {
    background: $surface;
    padding: 1 2;
    margin-bottom: 1;
    border-bottom: solid $border;
}

.progress-details {
    background: $surface;
    padding: 1 2;
}

.progress-stats {
    background: $surface;
    padding: 1 2;
    color: $text-secondary;
}

/* ===== Status Badges ===== */
.badge {
    background: $surface;
    border: solid $border;
    padding: 0 1;
}

.badge-success {
    background: rgba(63, 185, 80, 0.2);
    color: $success;
    border: solid $success;
}

.badge-warning {
    background: rgba(210, 153, 34, 0.2);
    color: $warning;
    border: solid $warning;
}

.badge-error {
    background: rgba(248, 81, 73, 0.2);
    color: $error;
    border: solid $error;
}

.badge-info {
    background: rgba(88, 166, 255, 0.2);
    color: $info;
    border: solid $info;
}

/* ===== Loading Spinner ===== */
.spinner {
    color: $accent;
    text-style: bold;
}

.loading-text {
    color: $text-secondary;
}

/* ===== Modal ===== */
.modal-overlay {
    background: rgba(13, 17, 23, 0.7);
}

.modal {
    background: $surface;
    border: thick $primary-dim;
    padding: 3;
}

.modal-title {
    color: $primary-bright;
    text-style: bold;
    border-bottom: solid $border;
    padding-bottom: 1;
    margin-bottom: 2;
}

/* ===== Existing Status Classes ===== */
.status-up-to-date {
    color: $success;
}

.status-update-available {
    color: $warning;
}

.status-checking {
    color: $info;
}

.status-error {
    color: $error;
}

/* ===== Container Specific Styles ===== */
#quant-container {
    width: 100%;
    height: auto;
}

#quant-table {
    width: 100%;
    min-width: 50;
}

/* ===== Responsive Design ===== */

/* Desktop (default, 80+ columns) - Full experience */
Screen {
    /* Default styles apply */
}

/* Tablet (60-79 columns) - Compact layout */
.tablet DataTable {
    padding: 0 1;
}

.tablet #status-bar {
    height: auto;
}

.tablet Input {
    width: 100%;
}

/* Mobile (< 60 columns) - Minimal layout */
.mobile #status-bar {
    layout: vertical;
    height: auto;
}

.mobile DataTable {
    padding: 0;
    width: 100%;
}

.mobile Input {
    width: 100%;
}

.mobile .section-header {
    padding: 1;
}

.mobile Container {
    padding: 0;
}

.mobile Horizontal {
    layout: vertical;
}

/* Very small screens (< 40 columns) */
.tiny {
    /* Minimal viable layout */
}

.tiny DataTable {
    min-width: 100%;
}

.tiny .section-header {
    text-style: none;
    padding: 0 1;
}
"""


def get_theme_css() -> str:
    """Get the current theme CSS."""
    return DARK_THEME_CSS


def get_color(color_name: str) -> str:
    """Get a color value from the theme."""
    return DARK_THEME.get(color_name, "#ffffff")
