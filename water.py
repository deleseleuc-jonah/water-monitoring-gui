import ctypes
import json
import os
import sys
from pathlib import Path


def configure_windows_dpi_awareness():
    """Set DPI handling before Tkinter or Matplotlib creates a window."""
    if sys.platform != "win32":
        return

    try:
        # Keep every window in this process on one stable system-DPI scale.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


configure_windows_dpi_awareness()

import PySimpleGUI as sg
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

from matplotlib.colors import is_color_like
from cycler import cycler
from scipy.stats import linregress, pearsonr, spearmanr


CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / "water-monitoring"
)

STATE_FILE = CONFIG_DIR / "state.json"
print(f"State file location: {STATE_FILE.resolve()}")
def save_state(window, values):
    state_values = {
        key: values[key]
        for key in PERSISTED_INPUT_KEYS
        if key in values
    }
    state_values["_schema_version"] = 1

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Write atomically so an interrupted save cannot corrupt the real file.
    temporary_file = STATE_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(state_values, indent=4),
        encoding="utf-8",
    )
    temporary_file.replace(STATE_FILE)


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not load saved state: {error}")
        return {}

# =========================
# Plot style
# =========================

plt.rcParams.update(
    {
        "figure.figsize": (12, 10),
        # Keep interactive plot windows at a normal screen resolution.
        "figure.dpi": 100,
        # Files saved from Matplotlib remain publication-quality.
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Segoe UI",  # Windows
            "Helvetica Neue",  # macOS
            "Arial",
            "Liberation Sans",  # Linux
            "DejaVu Sans",  # Matplotlib fallback
        ],
        "mathtext.fontset": "stix",
        "axes.linewidth": 1.0,
        "axes.labelsize": 11,
        "lines.linewidth": 2,
        "axes.labelweight": "bold",
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": "0.85",
        "grid.linestyle": "--",
        "grid.linewidth": 0.6,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "axes.prop_cycle": cycler(
            color=[
                "#0072B2",
                "#D55E00",
                "#009E73",
                "#CC79A7",
                "#E69F00",
                "#56B4E9",
                "#F0E442",
                "#000000",
            ]
        ),
    }
)

CHECKBOX_KEYS = [
    "-SIMPLE-LOGX-",
    "-SIMPLE-LOGY-",
    "-ADVANCED-LOGX-",
    "-ADVANCED-LOGY-",
    "-ADVANCED-GROUP?-",
    "-ADVANCED-LABELS?-",
    "-ADVANCED-LINEAR-REGRESSION-",
    "-ADVANCED-ONE-TO-ONE-LINE-",
    "-ADVANCED-PEARSON-",
    "-ADVANCED-SPEARMAN-",
    "-ADVANCED-SHADING-",
    "-ADVANCED-CONFIDENCE-INTERVALS-",
    "-ADVANCED-Y2-ENABLED-",
    "-ADVANCED-Y2-LOGY-",
    "-ADVANCED-Y2-LINEAR-REGRESSION-",
    "-ADVANCED-Y2-PEARSON-",
    "-ADVANCED-Y2-SPEARMAN-",
    "-ADVANCED-Y2-CONFIDENCE-INTERVALS-",
]

CHART_TYPES = ["Plot", "Scatter"]
MONTHS = list(range(1, 13))
GUI_FONT_SIZES = [10, 11, 12, 13, 14, 15, 16, 17, 18]
CHART_FONT_SIZES = list(range(6, 33))

# These defaults match the chart font sizes used before the options were added.
CHART_FONT_DEFAULTS = {
    "title": 12,
    "axis_label": 11,
    "tick_label": 8,
    "legend": 9,
    "data_label": 10,
    "report_title": 12,
    "report_text": 10,
}


# Every user-editable control whose value should survive a restart.
PERSISTED_INPUT_KEYS = [
    "FileSelect",
    "SheetSelect",
    "-README-SHEET-",
    "-README-NAME-",
    "-README-UNIT-",
    "-SIMPLE-X-",
    "-SIMPLE-Y-",
    "-SIMPLE-TYPE-",
    "-ADVANCED-X-",
    "-ADVANCED-Y-",
    "-ADVANCED-TYPE-",
    "-ADVANCED-GROUP-COL-",
    "-ADVANCED-GROUP-VALUES-",
    "-ADVANCED-LABEL-COL-",
    "-DRY-START-MONTH-",
    "-WET-START-MONTH-",
    "-DRY-RESTART-MONTH-",
    "-DRY-COLOR-",
    "-WET-COLOR-",
    "-ADVANCED-LOWER-LIMIT-COL-",
    "-ADVANCED-UPPER-LIMIT-COL-",
    "-ADVANCED-Y2-COL-",
    "-ADVANCED-Y2-TYPE-",
    "-ADVANCED-Y2-LOWER-LIMIT-COL-",
    "-ADVANCED-Y2-UPPER-LIMIT-COL-",
    "-SETTINGS-THEME-",
    "-SETTINGS-FONTSIZE-",
    "-SETTINGS-CHART-TITLE-FONTSIZE-",
    "-SETTINGS-CHART-AXIS-LABEL-FONTSIZE-",
    "-SETTINGS-CHART-TICK-LABEL-FONTSIZE-",
    "-SETTINGS-CHART-LEGEND-FONTSIZE-",
    "-SETTINGS-CHART-DATA-LABEL-FONTSIZE-",
    "-SETTINGS-CHART-REPORT-TITLE-FONTSIZE-",
    "-SETTINGS-CHART-REPORT-TEXT-FONTSIZE-",
] + CHECKBOX_KEYS

# Retrieve state if available
state = load_state()


def saved_choice(key, available_values, fallback=""):
    """Return saved data only when it remains an available choice."""
    saved_value = state.get(key, fallback)
    return saved_value if saved_value in available_values else fallback


def saved_boolean(key, fallback=False):
    saved_value = state.get(key, fallback)
    return saved_value if isinstance(saved_value, bool) else fallback


def saved_text(key, fallback=""):
    saved_value = state.get(key, fallback)
    return saved_value if isinstance(saved_value, str) else fallback


def saved_existing_file(key):
    saved_path = saved_text(key)
    return saved_path if saved_path and Path(saved_path).is_file() else ""


def saved_color(key, fallback):
    saved_value = saved_text(key, fallback)
    return saved_value if is_color_like(saved_value) else fallback


AVAILABLE_THEMES = sg.theme_list()
selected_theme = saved_choice(
    "-SETTINGS-THEME-",
    AVAILABLE_THEMES,
    sg.theme(),
)
selected_gui_font_size = saved_choice(
    "-SETTINGS-FONTSIZE-",
    GUI_FONT_SIZES,
    12,
)
selected_chart_title_font_size = saved_choice(
    "-SETTINGS-CHART-TITLE-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["title"],
)
selected_chart_axis_label_font_size = saved_choice(
    "-SETTINGS-CHART-AXIS-LABEL-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["axis_label"],
)
selected_chart_tick_label_font_size = saved_choice(
    "-SETTINGS-CHART-TICK-LABEL-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["tick_label"],
)
selected_chart_legend_font_size = saved_choice(
    "-SETTINGS-CHART-LEGEND-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["legend"],
)
selected_chart_data_label_font_size = saved_choice(
    "-SETTINGS-CHART-DATA-LABEL-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["data_label"],
)
selected_chart_report_title_font_size = saved_choice(
    "-SETTINGS-CHART-REPORT-TITLE-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["report_title"],
)
selected_chart_report_text_font_size = saved_choice(
    "-SETTINGS-CHART-REPORT-TEXT-FONTSIZE-",
    CHART_FONT_SIZES,
    CHART_FONT_DEFAULTS["report_text"],
)

sg.set_options(font=("Arial", selected_gui_font_size))
sg.theme(selected_theme)

# Apply the saved Matplotlib typography to charts created during this session.
plt.rcParams.update(
    {
        "axes.titlesize": selected_chart_title_font_size,
        "axes.labelsize": selected_chart_axis_label_font_size,
        "xtick.labelsize": selected_chart_tick_label_font_size,
        "ytick.labelsize": selected_chart_tick_label_font_size,
        "legend.fontsize": selected_chart_legend_font_size,
        "figure.titlesize": selected_chart_report_title_font_size,
    }
)

def add_season_shading(
    ax,
    dataframe,
    date_col,
    dry_color,
    wet_color,
    wet_start_month=5,
    dry_restart_month=11,
    alpha_dry=0.08,
    alpha_wet=0.06,
):
    temp = dataframe.dropna(subset=[date_col]).sort_values(date_col).copy()

    if temp.empty:
        return

    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])

    if temp.empty:
        return

    start_date = temp[date_col].min()
    end_date = temp[date_col].max()

    plot_start = pd.Timestamp(start_date.date())
    plot_end = pd.Timestamp(end_date.date())

    years = range(plot_start.year - 1, plot_end.year + 2)

    for year in years:
        season_blocks = [
            (
                pd.Timestamp(year=year, month=1, day=1),
                pd.Timestamp(year=year, month=wet_start_month, day=1),
                "Dry",
            ),
            (
                pd.Timestamp(year=year, month=wet_start_month, day=1),
                pd.Timestamp(year=year, month=dry_restart_month, day=1),
                "Wet",
            ),
            (
                pd.Timestamp(year=year, month=dry_restart_month, day=1),
                pd.Timestamp(year=year + 1, month=1, day=1),
                "Dry",
            ),
        ]

        for block_start, block_end, season in season_blocks:
            span_start = max(block_start, plot_start)
            span_end = min(block_end, plot_end)

            if span_start >= span_end:
                continue

            ax.axvspan(
                span_start,
                span_end,
                alpha=alpha_dry if season == "Dry" else alpha_wet,
                color=dry_color if season == "Dry" else wet_color,
                zorder=0,
            )

        for transition_date in [
            pd.Timestamp(year=year, month=wet_start_month, day=1),
            pd.Timestamp(year=year, month=dry_restart_month, day=1),
        ]:
            if plot_start <= transition_date <= plot_end:
                ax.axvline(
                    transition_date,
                    linestyle="--",
                    linewidth=1.0,
                    color="black",
                    alpha=0.7,
                    zorder=1,
                )

def read_excel(path, sheet=None):
    if sheet:
        return pd.read_excel(path, sheet_name=sheet)
    return pd.read_excel(path)


def read_metadata_excel(path, sheet):
    """Read a README sheet whose real headings may not be on its first row."""
    preview = pd.read_excel(
        path,
        sheet_name=sheet,
        header=None,
        nrows=25,
    )

    candidate_rows = []
    hinted_rows = []

    for row_index, row in preview.iterrows():
        cells = [
            str(value).strip()
            for value in row
            if pd.notna(value) and str(value).strip()
        ]
        if not cells:
            continue

        candidate_rows.append((row_index, len(cells)))
        normalized_cells = [cell.casefold() for cell in cells]

        has_name_heading = any(
            heading in cell
            for cell in normalized_cells
            for heading in ("name", "parameter", "paramètre", "parametre")
        )
        has_unit_heading = any(
            heading in cell
            for cell in normalized_cells
            for heading in ("unit", "unité", "unite")
        )

        if has_name_heading and has_unit_heading:
            hinted_rows.append(row_index)

    if hinted_rows:
        header_row = hinted_rows[0]
    elif candidate_rows:
        # Prefer the earliest row containing the greatest number of values.
        header_row = max(candidate_rows, key=lambda item: item[1])[0]
    else:
        raise ValueError("The selected README sheet is empty.")

    metadata = pd.read_excel(
        path,
        sheet_name=sheet,
        header=header_row,
    )
    metadata = metadata.dropna(axis=1, how="all")
    metadata.columns = [str(column).strip() for column in metadata.columns]

    named_columns = [
        column
        for column in metadata.columns
        if column and not column.casefold().startswith("unnamed:")
    ]

    if len(named_columns) >= 2:
        metadata = metadata.loc[:, named_columns]

    return metadata


def get_summary_df(data):
    return pd.DataFrame(
        {
            "Column": data.columns,
            "Type": data.dtypes.astype(str),
            "Non-Null": data.count().values,
            "Missing": data.isna().sum().values,
        }
    )


def clean_xy(data, x_col, y_col, log_x=False, log_y=False, label=None):
    cols = [x_col, y_col]
    if label:
        cols.append(label)

    plot_data = data[cols].dropna().copy()

    if log_x:
        plot_data = plot_data[plot_data[x_col] >= 0]

    if log_y:
        plot_data = plot_data[plot_data[y_col] >= 0]

    x_series = np.log10(plot_data[x_col] + 1) if log_x else plot_data[x_col]
    y_series = np.log10(plot_data[y_col] + 1) if log_y else plot_data[y_col]

    x_unit = meta_dict.get(x_col, "")
    y_unit = meta_dict.get(y_col, "")

    x_label = f"{x_col} ({x_unit})" if x_unit else x_col
    y_label = f"{y_col} ({y_unit})" if y_unit else y_col

    if log_x:
        x_label = f"log10({x_label} + 1)"

    if log_y:
        y_label = f"log10({y_label} + 1)"

    return x_series, y_series, x_label, y_label, plot_data


def simple_chart(data, values, meta_dict):
    if data is None:
        sg.popup("Please read a sheet first.")
        return

    try:
        x_col = values["-SIMPLE-X-"]
        y_col = values["-SIMPLE-Y-"]

        if not x_col or not y_col:
            sg.popup("Please select both X and Y columns.")
            return

        x_series, y_series, x_label, y_label, plot_data = clean_xy(
            data,
            x_col,
            y_col,
            values["-SIMPLE-LOGX-"],
            values["-SIMPLE-LOGY-"],
        )

        chart_type = values["-SIMPLE-TYPE-"]

        fig, ax = plt.subplots()
        ax.set_title(f"{y_label} as a function of {x_label} (n={len(plot_data)})")
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        if chart_type == "Plot":
            ax.plot(x_series, y_series, label=y_label)
        elif chart_type == "Scatter":
            ax.scatter(x_series, y_series, label=y_label)

        ax.legend(facecolor="white", edgecolor="black", framealpha=1)
        plt.show()
    except Exception as e:
        sg.popup_error(
            "Unable to generate the chart.\n\n"
            f"Reason:\n{e}\n\n"
            "Possible causes:\n"
            "• Log10 can only be applied to numeric data.\n"
            "• Dates and text cannot be log-transformed.\n"
            "• The selected columns may contain incompatible data types."
        )


def advanced_chart(data, values, meta_dict):
    if data is None:
        sg.popup("Please read a sheet first.")
        return

    try:
        x_col = values["-ADVANCED-X-"]
        y_col = values["-ADVANCED-Y-"]
        chart_type = values["-ADVANCED-TYPE-"]

        group_enabled = values["-ADVANCED-GROUP?-"]
        group_col = values["-ADVANCED-GROUP-COL-"]
        selected_groups = values["-ADVANCED-GROUP-VALUES-"]

        label_enabled = values["-ADVANCED-LABELS?-"]
        label_col = values["-ADVANCED-LABEL-COL-"]

        log_x_enabled = values["-ADVANCED-LOGX-"]
        log_y_enabled = values["-ADVANCED-LOGY-"]
        linear_regression_enabled = values["-ADVANCED-LINEAR-REGRESSION-"]
        one_to_one_line_enabled = values["-ADVANCED-ONE-TO-ONE-LINE-"]
        pearson_cor_enabled = values["-ADVANCED-PEARSON-"]
        spearman_cor_enabled = values["-ADVANCED-SPEARMAN-"]
        confidence_intervals_enabled = values[
            "-ADVANCED-CONFIDENCE-INTERVALS-"
        ]
        lower_limit_col = values.get("-ADVANCED-LOWER-LIMIT-COL-")
        upper_limit_col = values.get("-ADVANCED-UPPER-LIMIT-COL-")

        y2_enabled = values.get("-ADVANCED-Y2-ENABLED-", False)
        y2_col = values.get("-ADVANCED-Y2-COL-")
        y2_chart_type = values.get("-ADVANCED-Y2-TYPE-", "Plot")
        y2_log_enabled = values.get("-ADVANCED-Y2-LOGY-", False)
        y2_regression_enabled = values.get(
            "-ADVANCED-Y2-LINEAR-REGRESSION-", False
        )
        y2_pearson_enabled = values.get("-ADVANCED-Y2-PEARSON-", False)
        y2_spearman_enabled = values.get("-ADVANCED-Y2-SPEARMAN-", False)
        y2_confidence_enabled = values.get(
            "-ADVANCED-Y2-CONFIDENCE-INTERVALS-", False
        )
        y2_lower_limit_col = values.get(
            "-ADVANCED-Y2-LOWER-LIMIT-COL-"
        )
        y2_upper_limit_col = values.get(
            "-ADVANCED-Y2-UPPER-LIMIT-COL-"
        )

        if not x_col or not y_col:
            sg.popup("Please select both X and primary Y columns.")
            return

        if y2_enabled and not y2_col:
            sg.popup("Please select a secondary Y variable.")
            return

        if label_enabled and not label_col:
            sg.popup("Please select a label column.")
            return

        if group_enabled:
            if not group_col:
                sg.popup("Please select a grouping column.")
                return
            if not selected_groups:
                sg.popup("Please select at least one group value.")
                return

        def validate_interval(enabled, lower_col, upper_col, axis_name):
            if not enabled:
                return True
            if not lower_col or not upper_col:
                sg.popup(
                    f"Please select both lower and upper confidence "
                    f"interval columns for {axis_name}."
                )
                return False
            missing = [
                column
                for column in (lower_col, upper_col)
                if column not in data.columns
            ]
            if missing:
                sg.popup(
                    f"The following {axis_name} confidence interval "
                    "columns were not found:\n\n" + "\n".join(missing)
                )
                return False
            return True

        if not validate_interval(
            confidence_intervals_enabled,
            lower_limit_col,
            upper_limit_col,
            "primary Y",
        ):
            return

        if not validate_interval(
            y2_enabled and y2_confidence_enabled,
            y2_lower_limit_col,
            y2_upper_limit_col,
            "secondary Y",
        ):
            return

        fig, ax = plt.subplots()
        ax2 = ax.twinx() if y2_enabled else None
        correlation_lines = []

        if values.get("-ADVANCED-SHADING-", False):
            add_season_shading(
                ax,
                data,
                x_col,
                values.get("-DRY-COLOR-", "orange"),
                values.get("-WET-COLOR-", "blue"),
                int(values.get("-WET-START-MONTH-", 5)),
                int(values.get("-DRY-RESTART-MONTH-", 11)),
            )

        def draw_series(
            source,
            target_ax,
            selected_y_col,
            selected_chart_type,
            log_y,
            series_name,
            label_name,
            draw_data=True,
            draw_regression=True,
            draw_labels=False,
            draw_confidence=False,
            lower_col=None,
            upper_col=None,
            regression_enabled=False,
            pearson_enabled=False,
            spearman_enabled=False,
        ):
            x_series, y_series, x_label, y_label, plot_data = clean_xy(
                source,
                x_col,
                selected_y_col,
                log_x_enabled,
                log_y,
                label=label_col if (label_enabled and draw_labels) else None,
            )

            if draw_data:
                display_label = (
                    f"{series_name}: {label_name} (n={len(plot_data)})"
                    if group_enabled
                    else series_name
                )
                if selected_chart_type == "Plot":
                    target_ax.plot(
                        x_series,
                        y_series,
                        marker="o",
                        label=display_label,
                    )
                else:
                    target_ax.scatter(
                        x_series,
                        y_series,
                        label=display_label,
                    )

            if len(plot_data) >= 2:
                x_values = np.asarray(x_series)
                y_values = np.asarray(y_series, dtype=float)

                numeric_x = np.issubdtype(x_values.dtype, np.number)
                if numeric_x:
                    finite_mask = (
                        np.isfinite(x_values)
                        & np.isfinite(y_values)
                    )
                    statistic_x = x_values[finite_mask]
                    statistic_y = y_values[finite_mask]
                else:
                    statistic_x = np.array([])
                    statistic_y = np.array([])

                if (
                    regression_enabled
                    and draw_regression
                    and len(statistic_x) >= 2
                ):
                    regression = linregress(statistic_x, statistic_y)
                    x_line = np.linspace(
                        statistic_x.min(), statistic_x.max(), 100
                    )
                    y_line = regression.slope * x_line + regression.intercept
                    target_ax.plot(
                        x_line,
                        y_line,
                        "--",
                        linewidth=2,
                        label=f"{series_name} line of best fit",
                    )
                    correlation_lines.append(
                        f"{series_name} — {label_name} linear regression: "
                        f"y = {regression.slope:.3f}x "
                        f"+ {regression.intercept:.3f}"
                    )

                if pearson_enabled and len(statistic_x) >= 2:
                    result = pearsonr(statistic_x, statistic_y)
                    r = float(result.statistic)
                    p = float(result.pvalue)
                    correlation_lines.append(
                        f"{series_name} — {label_name} Pearson: "
                        f"r={r:.3f}, R²={r ** 2:.3f}, "
                        f"p={p:.3g}, n={len(statistic_x)}"
                    )

                if spearman_enabled and len(statistic_x) >= 2:
                    result = spearmanr(statistic_x, statistic_y)
                    rho = float(result.statistic)
                    p = float(result.pvalue)
                    correlation_lines.append(
                        f"{series_name} — {label_name} Spearman: "
                        f"ρ={rho:.3f}, p={p:.3g}, "
                        f"n={len(statistic_x)}"
                    )

            if label_enabled and draw_labels:
                for point_label, x_value, y_value in zip(
                    plot_data[label_col], x_series, y_series
                ):
                    target_ax.annotate(
                        str(point_label),
                        (x_value, y_value),
                        textcoords="offset points",
                        xytext=(4, 4),
                        fontsize=selected_chart_data_label_font_size,
                    )

            if draw_confidence and lower_col and upper_col:
                retained_index = plot_data.index
                lower_values = pd.to_numeric(
                    source.loc[retained_index, lower_col],
                    errors="coerce",
                ).to_numpy(dtype=float)
                upper_values = pd.to_numeric(
                    source.loc[retained_index, upper_col],
                    errors="coerce",
                ).to_numpy(dtype=float)
                interval_x = np.asarray(x_series)

                interval_mask = (
                    pd.notna(interval_x)
                    & np.isfinite(lower_values)
                    & np.isfinite(upper_values)
                )

                if log_y:
                    interval_mask &= (
                        (lower_values >= 0)
                        & (upper_values >= 0)
                    )
                    lower_values = np.where(
                        lower_values >= 0,
                        np.log10(lower_values + 1),
                        np.nan,
                    )
                    upper_values = np.where(
                        upper_values >= 0,
                        np.log10(upper_values + 1),
                        np.nan,
                    )

                valid_x = interval_x[interval_mask]
                valid_lower = lower_values[interval_mask]
                valid_upper = upper_values[interval_mask]

                if len(valid_x) >= 2:
                    order = np.argsort(valid_x)
                    target_ax.fill_between(
                        valid_x[order],
                        np.minimum(
                            valid_lower[order], valid_upper[order]
                        ),
                        np.maximum(
                            valid_lower[order], valid_upper[order]
                        ),
                        alpha=0.2,
                        label=f"{series_name} confidence interval",
                    )

            return x_label, y_label, len(plot_data)

        if group_enabled:
            selected_group_strings = [str(v) for v in selected_groups]
            all_group_data = data[
                data[group_col].astype(str).isin(selected_group_strings)
            ]
            total_n = 0

            for group_value in selected_groups:
                group_data = data[
                    data[group_col].astype(str) == str(group_value)
                ]
                x_label, y_label, count = draw_series(
                    group_data,
                    ax,
                    y_col,
                    chart_type,
                    log_y_enabled,
                    y_col,
                    str(group_value),
                    draw_data=True,
                    draw_regression=False,
                    draw_labels=True,
                    draw_confidence=confidence_intervals_enabled,
                    lower_col=lower_limit_col,
                    upper_col=upper_limit_col,
                    regression_enabled=linear_regression_enabled,
                    pearson_enabled=pearson_cor_enabled,
                    spearman_enabled=spearman_cor_enabled,
                )
                total_n += count

                if y2_enabled:
                    _, y2_label, _ = draw_series(
                        group_data,
                        ax2,
                        y2_col,
                        y2_chart_type,
                        y2_log_enabled,
                        y2_col,
                        str(group_value),
                        draw_data=True,
                        draw_regression=False,
                        draw_labels=False,
                        draw_confidence=y2_confidence_enabled,
                        lower_col=y2_lower_limit_col,
                        upper_col=y2_upper_limit_col,
                        regression_enabled=y2_regression_enabled,
                        pearson_enabled=y2_pearson_enabled,
                        spearman_enabled=y2_spearman_enabled,
                    )

            draw_series(
                all_group_data,
                ax,
                y_col,
                chart_type,
                log_y_enabled,
                y_col,
                "All selected groups",
                draw_data=False,
                draw_regression=True,
                draw_labels=False,
                draw_confidence=False,
                regression_enabled=linear_regression_enabled,
                pearson_enabled=pearson_cor_enabled,
                spearman_enabled=spearman_cor_enabled,
            )

            if y2_enabled:
                draw_series(
                    all_group_data,
                    ax2,
                    y2_col,
                    y2_chart_type,
                    y2_log_enabled,
                    y2_col,
                    "All selected groups",
                    draw_data=False,
                    draw_regression=True,
                    draw_labels=False,
                    draw_confidence=False,
                    regression_enabled=y2_regression_enabled,
                    pearson_enabled=y2_pearson_enabled,
                    spearman_enabled=y2_spearman_enabled,
                )

            title = (
                f"{y_label}"
                + (f" and {y2_label}" if y2_enabled else "")
                + f" as a function of {x_label}, "
                f"grouped by {group_col} (primary n={total_n})"
            )
        else:
            x_label, y_label, primary_n = draw_series(
                data,
                ax,
                y_col,
                chart_type,
                log_y_enabled,
                y_col,
                "All data",
                draw_data=True,
                draw_regression=True,
                draw_labels=True,
                draw_confidence=confidence_intervals_enabled,
                lower_col=lower_limit_col,
                upper_col=upper_limit_col,
                regression_enabled=linear_regression_enabled,
                pearson_enabled=pearson_cor_enabled,
                spearman_enabled=spearman_cor_enabled,
            )

            if y2_enabled:
                _, y2_label, secondary_n = draw_series(
                    data,
                    ax2,
                    y2_col,
                    y2_chart_type,
                    y2_log_enabled,
                    y2_col,
                    "All data",
                    draw_data=True,
                    draw_regression=True,
                    draw_labels=False,
                    draw_confidence=y2_confidence_enabled,
                    lower_col=y2_lower_limit_col,
                    upper_col=y2_upper_limit_col,
                    regression_enabled=y2_regression_enabled,
                    pearson_enabled=y2_pearson_enabled,
                    spearman_enabled=y2_spearman_enabled,
                )
                title = (
                    f"{y_label} and {y2_label} as a function of "
                    f"{x_label} (n₁={primary_n}, n₂={secondary_n})"
                )
            else:
                title = (
                    f"{y_label} as a function of "
                    f"{x_label} (n={primary_n})"
                )

        if one_to_one_line_enabled:
            ax.relim()
            ax.autoscale_view()
            x_limits = ax.get_xlim()
            y_limits = ax.get_ylim()
            line_min = max(x_limits[0], y_limits[0])
            line_max = min(x_limits[1], y_limits[1])
            if line_min < line_max:
                ax.plot(
                    [line_min, line_max],
                    [line_min, line_max],
                    linestyle=":",
                    color="black",
                    linewidth=2,
                    label="1:1 reference line",
                )

        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        if y2_enabled:
            ax2.set_ylabel(y2_label)
            ax2.grid(False)

        handles, legend_labels = ax.get_legend_handles_labels()
        if y2_enabled:
            handles2, labels2 = ax2.get_legend_handles_labels()
            handles += handles2
            legend_labels += labels2

        if handles:
            ax.legend(
                handles,
                legend_labels,
                facecolor="white",
                edgecolor="black",
                framealpha=1,
            )

        if correlation_lines:
            report_fig, report_ax = plt.subplots(figsize=(10, 6))
            report_ax.axis("off")
            report_ax.text(
                0.01,
                0.98,
                "\n".join(correlation_lines),
                ha="left",
                va="top",
                transform=report_ax.transAxes,
                fontsize=selected_chart_report_text_font_size,
            )
            report_fig.suptitle(
                "Statistical Report",
                fontweight="bold",
                fontsize=selected_chart_report_title_font_size,
            )

        plt.show()

    except Exception as e:
        sg.popup_error(
            "Unable to generate the chart.\n\n"
            f"Reason:\n{e}\n\n"
            "Possible causes:\n"
            "• Log10 can only be applied to numeric data.\n"
            "• Dates and text cannot be log-transformed.\n"
            "• The selected columns may contain incompatible data types."
        )

def stretch_scrollable_column_x(window, key):
    col = window[key]
    widget = col.Widget
    canvas = widget.canvas

    canvas_window_id = None
    for item in canvas.find_all():
        if canvas.type(item) == "window":
            canvas_window_id = item
            break

    if canvas_window_id is None:
        raise RuntimeError(f"No inner canvas window found for {key}")

    def resize_inner_frame(event):
        canvas.itemconfig(canvas_window_id, width=event.width)

    canvas.bind("<Configure>", resize_inner_frame)


def initialize_inputs(data):
    columns = data.columns.tolist()
    number_columns = data.select_dtypes(include=["number", "datetime", "boolean"]).columns.tolist()

    default_x = number_columns[0] if number_columns else ""
    default_y = number_columns[1] if len(number_columns) > 1 else ""

    window["-SIMPLE-X-"].update(
        values=number_columns,
        value=saved_choice("-SIMPLE-X-", number_columns, default_x),
    )
    window["-SIMPLE-Y-"].update(
        values=number_columns,
        value=saved_choice("-SIMPLE-Y-", number_columns, default_y),
    )

    window["-ADVANCED-X-"].update(
        values=number_columns,
        value=saved_choice("-ADVANCED-X-", number_columns, default_x),
    )
    window["-ADVANCED-Y-"].update(
        values=number_columns,
        value=saved_choice("-ADVANCED-Y-", number_columns, default_y),
    )
    window["-ADVANCED-Y2-COL-"].update(
        values=number_columns,
        value=saved_choice("-ADVANCED-Y2-COL-", number_columns),
    )
    window["-ADVANCED-Y2-LOWER-LIMIT-COL-"].update(
        values=number_columns,
        value=saved_choice(
            "-ADVANCED-Y2-LOWER-LIMIT-COL-", number_columns
        ),
    )
    window["-ADVANCED-Y2-UPPER-LIMIT-COL-"].update(
        values=number_columns,
        value=saved_choice(
            "-ADVANCED-Y2-UPPER-LIMIT-COL-", number_columns
        ),
    )
    group_col = saved_choice(
        "-ADVANCED-GROUP-COL-", columns
    )
    window["-ADVANCED-GROUP-COL-"].update(
        values=columns,
        value=group_col,
    )
    window["-ADVANCED-LABEL-COL-"].update(
        values=columns,
        value=saved_choice(
            "-ADVANCED-LABEL-COL-", columns
        ),
    )
    window["-ADVANCED-UPPER-LIMIT-COL-"].update(
        values=number_columns,
        value=saved_choice(
            "-ADVANCED-UPPER-LIMIT-COL-", number_columns
        ),
    )
    window["-ADVANCED-LOWER-LIMIT-COL-"].update(
        values=number_columns,
        value=saved_choice(
            "-ADVANCED-LOWER-LIMIT-COL-", number_columns
        ),
    )
    if group_col:
        group_values = sorted(data[group_col].dropna().astype(str).unique().tolist())
        saved_group_values = state.get("-ADVANCED-GROUP-VALUES-", [])
        if not isinstance(saved_group_values, list):
            saved_group_values = []
        selected_indices = [
            index
            for index, group_value in enumerate(group_values)
            if group_value in saved_group_values
        ]
        window["-ADVANCED-GROUP-VALUES-"].update(
            values=group_values,
            set_to_index=selected_indices,
        )
    else:
        window["-ADVANCED-GROUP-VALUES-"].update(values=[])


readme_layout = [
    [sg.Text("README Settings:")],
    [
        sg.Text("NAME column:"),
        sg.Combo(key="-README-NAME-", values=[], readonly=True, pad=(15, 0)),
        sg.Text("UNIT column:"),
        sg.Combo(key="-README-UNIT-", values=[], readonly=True, pad=(15, 0)),
    ],
    [
        sg.Button("Start", key="-START-", pad=(0, 30)),
    ],
]

sheet_group = sg.pin(
    sg.Column(
        [
            [
                sg.Text("Data Sheet:", pad=(0, 15)),
                sg.Combo(key="SheetSelect", values=[], readonly=True, pad=(15, 0)),
                sg.Text("README Sheet:", pad=(0, 15)),
                sg.Combo(key="-README-SHEET-", values=[], readonly=True, pad=(15, 0)),
                sg.Button("Read", key="-READ-SHEET-"),
            ],
            [
                sg.Column(
                    key="-README-GROUP-",
                    layout=readme_layout,
                    visible=False,
                    expand_x=True,
                    expand_y=True,
                    pad=(0, 0),
                )
            ],
        ],
        key="-SELECT-SHEET-",
        visible=False,
        expand_x=True,
        expand_y=True,
        pad=(0, 0),
    ),
    expand_x=True,
    expand_y=True,
)

excel_group = sg.pin(
    sg.Column(
        [
            [
                sg.Text(
                    "Welcome to Water Monitoring GUI. \n\n"
                    "To use this software, please select an excel file (.xlsx) with a data sheet and a metadata (readme) sheet.",
                    pad=(0, 15),
                )
            ],
            [sg.Text("Select a Data File (.xlsx):", pad=(0, 15))],
            [
                sg.Input(
                    key="FileSelect",
                    default_text=saved_existing_file("FileSelect"),
                ),
                sg.FileBrowse(target="FileSelect"),
                sg.Button("Read"),
            ],
            [sheet_group],
        ],
        key="-READ-",
        expand_x=True,
        expand_y=True,
        pad=(0, 0),
    )
)

summary_tab_contents = [
    [sg.Text("Data Summary:", font=("Arial", 14, "bold"))],
    [
        sg.Table(
            values=[],
            headings=["Column", "Type", "Non-Null", "Missing"],
            auto_size_columns=True,
            justification="left",
            num_rows=10,
            key="-SUMMARY-",
            expand_x=True,
            expand_y=True,
        )
    ],
]

summary_tab = [
    [sg.Column(layout=summary_tab_contents, expand_x=True, expand_y=True, pad=(30, 30))]
]

meta_tab_contents = [
    [sg.Text("Parameter Metadata:", font=("Arial", 14, "bold"))],
    [
        sg.Table(
            values=[],
            headings=["Name", "Unit"],
            auto_size_columns=True,
            justification="left",
            num_rows=10,
            key="-META-TABLE-",
            expand_x=True,
            expand_y=True,
        )
    ],
]

meta_tab = [
    [sg.Column(layout=meta_tab_contents, expand_x=True, expand_y=True, pad=(30, 30))]
]


simple_chart_contents = [
    [sg.Text("Simple Chart:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Text("X:"),
        sg.Combo(key="-SIMPLE-X-", values=[], readonly=True, expand_x=True),
        sg.Text("Y:"),
        sg.Combo(key="-SIMPLE-Y-", values=[], readonly=True, expand_x=True),
    ],
    [
        sg.Text("Chart type:", pad=(0, 30)),
        sg.Combo(
            key="-SIMPLE-TYPE-",
            values=CHART_TYPES,
            default_value=saved_choice(
                "-SIMPLE-TYPE-", CHART_TYPES, "Scatter"
            ),
            readonly=True,
        ),
        sg.Button("Plot", key="-SIMPLE-CHART-"),
    ],
    [
        sg.Checkbox(
            "Log10 x",
            key="-SIMPLE-LOGX-",
            default=saved_boolean("-SIMPLE-LOGX-"),
        ),
        sg.Checkbox(
            "Log10 y",
            key="-SIMPLE-LOGY-",
            default=saved_boolean("-SIMPLE-LOGY-"),
        ),
    ],
]

simple_chart_tab = [
    [
        sg.Column(
            layout=simple_chart_contents,
            expand_x=True,
            expand_y=True,
            scrollable=True,
            vertical_scroll_only=True,
            pad=(30, 30),
            key="-SIMPLE-CHART-SCROLLABLE-",
        )
    ]
]

advanced_chart_inner = [
    [sg.Text("Advanced Chart:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Text("X:"),
        sg.Combo(key="-ADVANCED-X-", values=[], readonly=True, expand_x=True),
        sg.Text("Y:"),
        sg.Combo(key="-ADVANCED-Y-", values=[], readonly=True, expand_x=True),
    ], #chose x and y
    [
        sg.Text("Chart type:", pad=(0, 30)),
        sg.Combo(
            key="-ADVANCED-TYPE-",
            values=CHART_TYPES,
            default_value=saved_choice(
                "-ADVANCED-TYPE-", CHART_TYPES, "Scatter"
            ),
            readonly=True,
        ),
        sg.Button("Plot", key="-ADVANCED-CHART-"),
    ], #choose scatter or plot
    [
        sg.Checkbox(
            "Log10 x",
            key="-ADVANCED-LOGX-",
            default=saved_boolean("-ADVANCED-LOGX-"),
        ),
        sg.Checkbox(
            "Log10 y",
            key="-ADVANCED-LOGY-",
            default=saved_boolean("-ADVANCED-LOGY-"),
        ),
        sg.Checkbox(
            "Linear Regression",
            key="-ADVANCED-LINEAR-REGRESSION-",
            default=saved_boolean("-ADVANCED-LINEAR-REGRESSION-"),
        ),
        sg.Checkbox(
            "1:1 Reference Line",
            key="-ADVANCED-ONE-TO-ONE-LINE-",
            default=saved_boolean("-ADVANCED-ONE-TO-ONE-LINE-"),
        ),
        sg.Checkbox(
            "Pearson Correlation",
            key="-ADVANCED-PEARSON-",
            default=saved_boolean("-ADVANCED-PEARSON-"),
        ),
        sg.Checkbox(
            "Spearman Correlation",
            key="-ADVANCED-SPEARMAN-",
            default=saved_boolean("-ADVANCED-SPEARMAN-"),
        ),
    ], #data options; log, correlation, linear regression
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Grouping:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Checkbox(
            "Activate Grouping",
            key="-ADVANCED-GROUP?-",
            default=saved_boolean("-ADVANCED-GROUP?-"),
        ),
    ], #activate grouping
    [
        sg.Text("Group column:"),
        sg.Combo(
            key="-ADVANCED-GROUP-COL-",
            values=[],
            readonly=True,
            enable_events=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ], #grouping column
    [
        sg.Text("Group values:"),
    ],
    [
        sg.Listbox(
            key="-ADVANCED-GROUP-VALUES-",
            values=[],
            select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
            size=(40, 8),
            expand_x=True,
            pad=(0, 15),
        )
    ], #grouping values
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Labels:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Checkbox(
            "Activate Labels",
            key="-ADVANCED-LABELS?-",
            default=saved_boolean("-ADVANCED-LABELS?-"),
        ),
    ], #activate labels
    [
        sg.Text("Label column:"),
        sg.Combo(
            key="-ADVANCED-LABEL-COL-",
            values=[],
            readonly=True,
            enable_events=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ], #label column
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Season Shading:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Checkbox(
            "Enable season shading",
            key="-ADVANCED-SHADING-",
            default=saved_boolean("-ADVANCED-SHADING-"),
        ),
    ], #enable season shading
    [
        sg.Text("Dry season starts:"),
        sg.Combo(
            values=MONTHS,
            default_value=saved_choice("-DRY-START-MONTH-", MONTHS, 1),
            key="-DRY-START-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
        sg.Text("Wet season starts:"),
        sg.Combo(
            values=MONTHS,
            default_value=saved_choice("-WET-START-MONTH-", MONTHS, 5),
            key="-WET-START-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
        sg.Text("Dry season starts again:"),
        sg.Combo(
            values=MONTHS,
            default_value=saved_choice("-DRY-RESTART-MONTH-", MONTHS, 11),
            key="-DRY-RESTART-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
    ], #season options
    [
        sg.Text("Dry season color:"),
        sg.Input(
            saved_color("-DRY-COLOR-", "orange"),
            key="-DRY-COLOR-",
            size=(12, 1),
        ),
        sg.ColorChooserButton("Choose", target="-DRY-COLOR-"),
    ], #dry color
    [
        sg.Text("Wet season color:"),
        sg.Input(
            saved_color("-WET-COLOR-", "blue"),
            key="-WET-COLOR-",
            size=(12, 1),
        ),
        sg.ColorChooserButton("Choose", target="-WET-COLOR-"),
    ], #wet color
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Confidence Intervals:", pad=(0, 30), font=("Arial", 14, "bold"))],
    [
        sg.Checkbox(
            "Enable confidence intervals",
            key="-ADVANCED-CONFIDENCE-INTERVALS-",
            default=saved_boolean("-ADVANCED-CONFIDENCE-INTERVALS-"),
        ),
    ],
    [
        sg.Text("Lower limit column:"),
        sg.Combo(
            key="-ADVANCED-LOWER-LIMIT-COL-",
            values=[],
            readonly=True,
            enable_events=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ],  # Lower limit column,
    [
        sg.Text("Upper limit column:"),
        sg.Combo(
            key="-ADVANCED-UPPER-LIMIT-COL-",
            values=[],
            readonly=True,
            enable_events=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ],  # Upper limit column,
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Second Y Axis:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        sg.Checkbox(
            "Activate second Y axis",
            key="-ADVANCED-Y2-ENABLED-",
            default=saved_boolean("-ADVANCED-Y2-ENABLED-"),
        ),
    ],
    [
        sg.Text("Second Y variable:"),
        sg.Combo(
            key="-ADVANCED-Y2-COL-",
            values=[],
            readonly=True,
            expand_x=True,
            pad=(0, 15),
        ),
        sg.Text("Chart type:"),
        sg.Combo(
            key="-ADVANCED-Y2-TYPE-",
            values=CHART_TYPES,
            default_value=saved_choice(
                "-ADVANCED-Y2-TYPE-", CHART_TYPES, "Plot"
            ),
            readonly=True,
        ),
    ],
    [
        sg.Checkbox(
            "Log10 second Y",
            key="-ADVANCED-Y2-LOGY-",
            default=saved_boolean("-ADVANCED-Y2-LOGY-"),
        ),
        sg.Checkbox(
            "Linear Regression",
            key="-ADVANCED-Y2-LINEAR-REGRESSION-",
            default=saved_boolean("-ADVANCED-Y2-LINEAR-REGRESSION-"),
        ),
        sg.Checkbox(
            "Pearson Correlation",
            key="-ADVANCED-Y2-PEARSON-",
            default=saved_boolean("-ADVANCED-Y2-PEARSON-"),
        ),
        sg.Checkbox(
            "Spearman Correlation",
            key="-ADVANCED-Y2-SPEARMAN-",
            default=saved_boolean("-ADVANCED-Y2-SPEARMAN-"),
        ),
    ],
    [
        sg.Checkbox(
            "Enable second Y confidence intervals",
            key="-ADVANCED-Y2-CONFIDENCE-INTERVALS-",
            default=saved_boolean(
                "-ADVANCED-Y2-CONFIDENCE-INTERVALS-"
            ),
        ),
    ],
    [
        sg.Text("Second Y lower limit column:"),
        sg.Combo(
            key="-ADVANCED-Y2-LOWER-LIMIT-COL-",
            values=[],
            readonly=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ],
    [
        sg.Text("Second Y upper limit column:"),
        sg.Combo(
            key="-ADVANCED-Y2-UPPER-LIMIT-COL-",
            values=[],
            readonly=True,
            expand_x=True,
            pad=(0, 15),
        ),
    ],

]
advanced_chart_contents = [
    [sg.Column(layout=advanced_chart_inner, expand_x=True, expand_y=True, pad=(30, 0))]
]

advanced_chart_tab = [
    [
        sg.Column(
            layout=advanced_chart_contents,
            scrollable=True,
            vertical_scroll_only=True,
            expand_y=True,
            expand_x=True,
            key="-ADVANCED-CHART-SCROLLABLE-",
            pad=(30, 15),
        )
    ]
]

settings_tab = [
    [
        sg.Column(
            layout=[
                [
                    sg.Text(
                        "Note: Save & Exit, then restart the application "
                        "to apply these settings."
                    )
                ],
                [
                    sg.Text(
                        "GUI Appearance",
                        font=("Arial", 14, "bold"),
                        pad=(0, 15),
                    )
                ],
                [
                    sg.Text(
                        "These options affect application controls, "
                        "not Matplotlib chart text."
                    )
                ],
                [
                    sg.Text("GUI theme:", size=(34, 1), pad=(0, 15)),
                    sg.Combo(
                        values=AVAILABLE_THEMES,
                        key="-SETTINGS-THEME-",
                        default_value=selected_theme,
                        readonly=True,
                    ),
                ],
                [
                    sg.Text(
                        "GUI font size (controls):",
                        size=(34, 1),
                        pad=(0, 30),
                    ),
                    sg.Combo(
                        key="-SETTINGS-FONTSIZE-",
                        values=GUI_FONT_SIZES,
                        default_value=selected_gui_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [sg.HSep(pad=(0, 20))],
                [
                    sg.Text(
                        "Chart Font Sizes (Matplotlib)",
                        font=("Arial", 14, "bold"),
                        pad=(0, 15),
                    )
                ],
                [
                    sg.Text(
                        "These options affect newly created charts and "
                        "statistical reports, not the GUI."
                    )
                ],
                [
                    sg.Text(
                        "Chart title (axes title):",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-TITLE-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_title_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "X/Y axis labels:",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-AXIS-LABEL-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_axis_label_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "X/Y tick labels:",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-TICK-LABEL-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_tick_label_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "Legend text:",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-LEGEND-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_legend_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "Point/data labels (annotations):",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-DATA-LABEL-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_data_label_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "Statistical report title:",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-REPORT-TITLE-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_report_title_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
                [
                    sg.Text(
                        "Statistical report text:",
                        size=(34, 1),
                        pad=(0, 10),
                    ),
                    sg.Combo(
                        key="-SETTINGS-CHART-REPORT-TEXT-FONTSIZE-",
                        values=CHART_FONT_SIZES,
                        default_value=selected_chart_report_text_font_size,
                        readonly=True,
                        size=(6, 1),
                    ),
                ],
            ],
            expand_x=True,
            expand_y=True,
            key="-SETTINGS-TAB-",
            pad=(30, 30),
        )
    ]
]

tabs_group = sg.pin(
    sg.Column(
        [
            [
                sg.TabGroup(
                    [
                        [
                            sg.Tab("Summary", summary_tab),
                            sg.Tab("Simple Chart", simple_chart_tab),
                            sg.Tab("Advanced Chart", advanced_chart_tab),
                            sg.Tab("Metadata", meta_tab),
                            sg.Tab("Settings", settings_tab),
                        ]
                    ],
                    key="-TABGROUP-",
                    expand_x=True,
                    expand_y=True,
                )
            ]
        ],
        key="-TABS-GROUP-",
        visible=False,
        expand_x=True,
        expand_y=True,
    ),
    expand_x=True,
    expand_y=True,
)

layout = [
    [
        sg.Text("Water Monitoring GUI", font=("Arial", 20, "bold")),
        sg.Text("💧", font=("Segoe UI Emoji", 30)),
        sg.Column(layout=[], expand_x=True),
        sg.Button("Save & Exit", key="-SAVE-AND-EXIT-", visible=False),
    ],
    [sg.HSep(pad=(0, 30))],
    [excel_group],
    [tabs_group],
    [sg.HSep(pad=(0, 30))],
    [sg.Text("by Jonah de Léséleuc ©2026 rights reserved")],
]

window = sg.Window(
    title="GUI",
    layout=layout,
    size=(1920, 1080),
    resizable=True,
    margins=(100, 50),
    finalize=True,
)

stretch_scrollable_column_x(window, "-ADVANCED-CHART-SCROLLABLE-")
stretch_scrollable_column_x(window, "-SIMPLE-CHART-SCROLLABLE-")

data = pd.DataFrame
meta = pd.DataFrame
meta_dict = dict()
excel = pd.DataFrame

data_sheet_name = ""
meta_sheet_name = ""

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == "-SAVE-AND-EXIT-":
        save_state(window, values)
        break
    if event == "-READ-SHEET-":
        data_sheet_name = values["SheetSelect"]
        meta_sheet_name = values["-README-SHEET-"]

        available_sheet_names = getattr(excel, "sheet_names", [])
        if (
            data_sheet_name not in available_sheet_names
            or meta_sheet_name not in available_sheet_names
        ):
            sg.popup(
                "Please select an available data sheet and README sheet."
            )
            continue

        meta = read_metadata_excel(
            path=values["FileSelect"],
            sheet=meta_sheet_name,
        )
        data = read_excel(
            path=values["FileSelect"],
            sheet=data_sheet_name,
        )

        window["-README-GROUP-"].update(visible=True)
        metadata_columns = meta.columns.tolist()

        window["-README-NAME-"].update(
            values=metadata_columns,
            value=saved_choice("-README-NAME-", metadata_columns),
        )
        window["-README-UNIT-"].update(
            values=metadata_columns,
            value=saved_choice("-README-UNIT-", metadata_columns),
        )
    if event == "Read":
        try:
            excel = pd.ExcelFile(values["FileSelect"])
            sheet_names = excel.sheet_names
            window["SheetSelect"].update(
                values=sheet_names,
                value=saved_choice("SheetSelect", sheet_names),
            )
            window["-README-SHEET-"].update(
                values=sheet_names,
                value=saved_choice("-README-SHEET-", sheet_names),
            )
            window["-SELECT-SHEET-"].update(visible=True)
        except Exception as e:
            sg.popup_error(f"Could not read Excel file:\n{e}")

    if event == "-START-":
        try:
            name_col = values["-README-NAME-"]
            unit_col = values["-README-UNIT-"]

            if name_col not in meta.columns or unit_col not in meta.columns:
                raise ValueError(
                    "Please select available NAME and UNIT columns "
                    "from the README sheet."
                )

            meta_clean = meta.dropna(subset=[name_col]).copy()
            meta_clean[unit_col] = meta_clean[unit_col].fillna("")

            meta_dict = dict(zip(meta_clean[name_col], meta_clean[unit_col]))

            window["-META-TABLE-"].update(values=list(meta_dict.items()))

            window["-READ-"].update(visible=False)
            window["-SAVE-AND-EXIT-"].update(visible=True)

            summary = get_summary_df(data)
            window["-SUMMARY-"].update(values=summary.values.tolist())

            initialize_inputs(data)  # populate combos with available options

            window["-TABS-GROUP-"].update(visible=True)

        except Exception as e:
            sg.popup_error(f"Could not read sheet:\n{e}")

    if event == "-ADVANCED-GROUP-COL-" and data is not None:
        group_col = values["-ADVANCED-GROUP-COL-"]

        if group_col:
            group_values = sorted(
                data[group_col].dropna().astype(str).unique().tolist()
            )
            window["-ADVANCED-GROUP-VALUES-"].update(values=group_values)
        else:
            window["-ADVANCED-GROUP-VALUES-"].update(values=[])

    if event == "-SIMPLE-CHART-":
        simple_chart(data, values, meta_dict)

    if event == "-ADVANCED-CHART-":
        advanced_chart(data, values, meta_dict)

window.close()