import ctypes
import json
import math
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
        "font.family": "serif",
        "font.serif": ["Arial"],
        "mathtext.fontset": "stix",
        "font.size": 11,
        "axes.linewidth": 1.0,
        "axes.labelsize": 11,
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
        "lines.linewidth": 1.5,
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
    "-ADVANCED-PEARSON-",
    "-ADVANCED-SPEARMAN-",
    "-ADVANCED-SHADING-",
    "-ADVANCED-CONFIDENCE-INTERVALS-",
]

CHART_TYPES = ["Plot", "Scatter"]
MONTHS = list(range(1, 13))
FONT_SIZES = [10, 11, 12, 13, 14, 15, 16, 17, 18]


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
    "-SETTINGS-THEME-",
    "-SETTINGS-FONTSIZE-",
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
selected_font_size = saved_choice(
    "-SETTINGS-FONTSIZE-",
    FONT_SIZES,
    12,
)

sg.set_options(font=("Arial", selected_font_size))
sg.theme(selected_theme)

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


def _beta_continued_fraction(a, b, x):
    """Evaluate the continued fraction used by the incomplete beta function."""
    maximum_iterations = 200
    epsilon = 3e-14
    minimum_value = 1e-300

    combined = a + b
    a_plus_one = a + 1.0
    a_minus_one = a - 1.0

    c_value = 1.0
    d_value = 1.0 - combined * x / a_plus_one
    if abs(d_value) < minimum_value:
        d_value = minimum_value
    d_value = 1.0 / d_value
    result = d_value

    for iteration in range(1, maximum_iterations + 1):
        doubled_iteration = 2 * iteration
        coefficient = (
            iteration
            * (b - iteration)
            * x
            / (
                (a_minus_one + doubled_iteration)
                * (a + doubled_iteration)
            )
        )

        d_value = 1.0 + coefficient * d_value
        if abs(d_value) < minimum_value:
            d_value = minimum_value
        c_value = 1.0 + coefficient / c_value
        if abs(c_value) < minimum_value:
            c_value = minimum_value
        d_value = 1.0 / d_value
        result *= d_value * c_value

        coefficient = -(
            (a + iteration)
            * (combined + iteration)
            * x
            / (
                (a + doubled_iteration)
                * (a_plus_one + doubled_iteration)
            )
        )

        d_value = 1.0 + coefficient * d_value
        if abs(d_value) < minimum_value:
            d_value = minimum_value
        c_value = 1.0 + coefficient / c_value
        if abs(c_value) < minimum_value:
            c_value = minimum_value
        d_value = 1.0 / d_value

        delta = d_value * c_value
        result *= delta
        if abs(delta - 1.0) < epsilon:
            break

    return result


def _regularized_incomplete_beta(a, b, x):
    """Return the regularized incomplete beta function without SciPy."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    factor = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )

    if x < (a + 1.0) / (a + b + 2.0):
        return (
            factor
            * _beta_continued_fraction(a, b, x)
            / a
        )

    return 1.0 - (
        factor
        * _beta_continued_fraction(b, a, 1.0 - x)
        / b
    )


def _correlation_p_value(coefficient, sample_size):
    """Calculate a two-sided correlation p-value using Student's t test."""
    if sample_size < 3 or not math.isfinite(coefficient):
        return math.nan

    coefficient = min(max(float(coefficient), -1.0), 1.0)
    if abs(coefficient) == 1.0:
        return 0.0

    degrees_of_freedom = sample_size - 2
    beta_argument = 1.0 - coefficient ** 2
    p_value = _regularized_incomplete_beta(
        degrees_of_freedom / 2.0,
        0.5,
        beta_argument,
    )
    return min(max(p_value, 0.0), 1.0)


def _correlation_coefficient(x_values, y_values):
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)

    if len(x_values) != len(y_values) or len(x_values) < 2:
        return math.nan
    if np.ptp(x_values) == 0 or np.ptp(y_values) == 0:
        return math.nan

    return float(np.corrcoef(x_values, y_values)[0, 1])


def pearson_correlation(x_values, y_values):
    coefficient = _correlation_coefficient(x_values, y_values)
    sample_size = len(x_values)

    # Pearson's exact two-point test returns p=1 for either possible ordering.
    if sample_size == 2 and math.isfinite(coefficient):
        return coefficient, 1.0

    return coefficient, _correlation_p_value(
        coefficient,
        sample_size,
    )


def spearman_correlation(x_values, y_values):
    x_ranks = (
        pd.Series(np.asarray(x_values, dtype=float))
        .rank(method="average")
        .to_numpy(dtype=float)
    )
    y_ranks = (
        pd.Series(np.asarray(y_values, dtype=float))
        .rank(method="average")
        .to_numpy(dtype=float)
    )

    coefficient = _correlation_coefficient(x_ranks, y_ranks)
    return coefficient, _correlation_p_value(
        coefficient,
        len(x_ranks),
    )


def clean_xy(data, x_col, y_col, log_x=False, log_y=False, label=None):
    cols = [x_col, y_col]
    if label:
        cols.append(label)

    plot_data = data[cols].dropna().copy()

    if log_x:
        plot_data = plot_data[plot_data[x_col] > 0]

    if log_y:
        plot_data = plot_data[plot_data[y_col] > 0]

    x_series = np.log10(plot_data[x_col]) if log_x else plot_data[x_col]
    y_series = np.log10(plot_data[y_col]) if log_y else plot_data[y_col]

    x_unit = meta_dict.get(x_col, "")
    y_unit = meta_dict.get(y_col, "")

    x_label = f"{x_col} ({x_unit})" if x_unit else x_col
    y_label = f"{y_col} ({y_unit})" if y_unit else y_col

    if log_x:
        x_label = f"log10({x_label})"

    if log_y:
        y_label = f"log10({y_label})"

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

        linear_regression_enabled = values[
            "-ADVANCED-LINEAR-REGRESSION-"
        ]

        label_enabled = values["-ADVANCED-LABELS?-"]
        label_col = values["-ADVANCED-LABEL-COL-"]

        pearson_cor_enabled = values["-ADVANCED-PEARSON-"]
        spearman_cor_enabled = values["-ADVANCED-SPEARMAN-"]

        confidence_intervals_enabled = values[
            "-ADVANCED-CONFIDENCE-INTERVALS-"
        ]

        lower_limit_col = values.get(
            "-ADVANCED-LOWER-LIMIT-COL-"
        )
        upper_limit_col = values.get(
            "-ADVANCED-UPPER-LIMIT-COL-"
        )

        log_x_enabled = values["-ADVANCED-LOGX-"]
        log_y_enabled = values["-ADVANCED-LOGY-"]

        correlation_lines = []

        if not x_col or not y_col:
            sg.popup("Please select both X and Y columns.")
            return

        if label_enabled and not label_col:
            sg.popup("Please select a label column.")
            return

        if confidence_intervals_enabled:
            if not lower_limit_col or not upper_limit_col:
                sg.popup(
                    "Please select both lower and upper "
                    "confidence interval columns."
                )
                return

            missing_columns = [
                col
                for col in [lower_limit_col, upper_limit_col]
                if col not in data.columns
            ]

            if missing_columns:
                sg.popup(
                    "The following confidence interval columns "
                    "were not found:\n\n"
                    + "\n".join(missing_columns)
                )
                return

        fig, ax = plt.subplots()

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

        def handle_options(
            plot_data_source,
            label_name="All data",
            draw_regression=True,
            draw_labels=True,
            draw_confidence_interval=True,
        ):
            (
                x_series,
                y_series,
                x_label,
                y_label,
                plot_data,
            ) = clean_xy(
                plot_data_source,
                x_col,
                y_col,
                log_x_enabled,
                log_y_enabled,
                label=label_col if label_enabled else None,
            )

            if len(x_series) < 2:
                return

            x_values = np.asarray(x_series)
            y_values = np.asarray(y_series, dtype=float)

            if linear_regression_enabled and draw_regression:
                # Linear regression requires a numeric X axis.
                if np.issubdtype(x_values.dtype, np.number):
                    regression_mask = (
                        np.isfinite(x_values)
                        & np.isfinite(y_values)
                    )

                    regression_x = x_values[regression_mask]
                    regression_y = y_values[regression_mask]

                    if len(regression_x) >= 2:
                        m, b = np.polyfit(
                            regression_x,
                            regression_y,
                            1,
                        )

                        x_line = np.linspace(
                            regression_x.min(),
                            regression_x.max(),
                            100,
                        )
                        y_line = m * x_line + b

                        ax.plot(
                            x_line,
                            y_line,
                            "--",
                            color="black",
                            linewidth=2,
                            label="Line of best fit",
                        )

                        correlation_lines.append(
                            f"{label_name} linear regression: "
                            f"y = {m:.3f}x + {b:.3f}"
                        )

            if pearson_cor_enabled:
                if np.issubdtype(x_values.dtype, np.number):
                    correlation_mask = (
                        np.isfinite(x_values)
                        & np.isfinite(y_values)
                    )

                    correlation_x = x_values[correlation_mask]
                    correlation_y = y_values[correlation_mask]

                    if len(correlation_x) >= 2:
                        r, p = pearson_correlation(
                            correlation_x,
                            correlation_y,
                        )

                        correlation_lines.append(
                            f"{label_name} Pearson: "
                            f"r={r:.3f}, "
                            f"R²={r ** 2:.3f}, "
                            f"p={p:.3g}, "
                            f"n={len(correlation_x)}"
                        )

            if spearman_cor_enabled:
                if np.issubdtype(x_values.dtype, np.number):
                    correlation_mask = (
                        np.isfinite(x_values)
                        & np.isfinite(y_values)
                    )

                    correlation_x = x_values[correlation_mask]
                    correlation_y = y_values[correlation_mask]

                    if len(correlation_x) >= 2:
                        rho, p = spearman_correlation(
                            correlation_x,
                            correlation_y,
                        )

                        correlation_lines.append(
                            f"{label_name} Spearman: "
                            f"ρ={rho:.3f}, "
                            f"p={p:.3g}, "
                            f"n={len(correlation_x)}"
                        )

            if label_enabled and draw_labels:
                for label, x, y in zip(
                    plot_data[label_col],
                    x_series,
                    y_series,
                ):
                    ax.annotate(
                        str(label),
                        (x, y),
                        fontsize=7,
                        textcoords="offset points",
                        xytext=(4, 4),
                    )

            if (
                confidence_intervals_enabled
                and draw_confidence_interval
            ):
                if (
                        confidence_intervals_enabled
                        and draw_confidence_interval
                ):
                    # clean_xy may return only X, Y, and label columns.
                    # Use its retained indexes to retrieve the corresponding
                    # confidence limits from the original data source.
                    retained_index = plot_data.index

                    lower_values = pd.to_numeric(
                        plot_data_source.loc[
                            retained_index,
                            lower_limit_col,
                        ],
                        errors="coerce",
                    ).to_numpy(dtype=float)

                    upper_values = pd.to_numeric(
                        plot_data_source.loc[
                            retained_index,
                            upper_limit_col,
                        ],
                        errors="coerce",
                    ).to_numpy(dtype=float)

                    interval_x = np.asarray(x_series)

                    # Only draw an interval where X, lower, and upper
                    # values are all available.
                    interval_mask = (
                            pd.notna(interval_x)
                            & np.isfinite(lower_values)
                            & np.isfinite(upper_values)
                    )

                    if log_y_enabled:
                        interval_mask &= (
                                (lower_values > 0)
                                & (upper_values > 0)
                        )

                        lower_values = np.where(
                            lower_values > 0,
                            np.log10(lower_values),
                            np.nan,
                        )

                        upper_values = np.where(
                            upper_values > 0,
                            np.log10(upper_values),
                            np.nan,
                        )

                    valid_x = interval_x[interval_mask]
                    valid_lower = lower_values[interval_mask]
                    valid_upper = upper_values[interval_mask]

                    if len(valid_x) >= 2:
                        sort_order = np.argsort(valid_x)

                        valid_x = valid_x[sort_order]
                        valid_lower = valid_lower[sort_order]
                        valid_upper = valid_upper[sort_order]

                        ax.fill_between(
                            valid_x,
                            np.minimum(valid_lower, valid_upper),
                            np.maximum(valid_lower, valid_upper),
                            alpha=0.2,
                            label=f"{label_name} confidence interval",
                        )

        if group_enabled:
            if not group_col:
                sg.popup("Please select a grouping column.")
                return

            if not selected_groups:
                sg.popup(
                    "Please select at least one group value."
                )
                return

            total_n = 0

            selected_group_strings = [
                str(group)
                for group in selected_groups
            ]

            all_group_data = data[
                data[group_col]
                .astype(str)
                .isin(selected_group_strings)
            ]

            for group_value in selected_groups:
                group_data = data[
                    data[group_col].astype(str)
                    == str(group_value)
                ]

                (
                    x_series,
                    y_series,
                    x_label,
                    y_label,
                    plot_data,
                ) = clean_xy(
                    group_data,
                    x_col,
                    y_col,
                    log_x_enabled,
                    log_y_enabled,
                    label=(
                        label_col
                        if label_enabled
                        else None
                    ),
                )

                total_n += len(plot_data)

                group_label = (
                    f"{group_value} "
                    f"(n={len(plot_data)})"
                )

                if chart_type == "Plot":
                    ax.plot(
                        x_series,
                        y_series,
                        marker="o",
                        label=group_label,
                    )

                elif chart_type == "Scatter":
                    ax.scatter(
                        x_series,
                        y_series,
                        label=group_label,
                    )

                handle_options(
                    group_data,
                    label_name=str(group_value),
                    draw_regression=False,
                    draw_labels=True,
                    draw_confidence_interval=True,
                )

            # Calculate regression and correlations across all selected
            # groups, but do not add another combined confidence band.
            handle_options(
                all_group_data,
                label_name="All selected groups",
                draw_regression=True,
                draw_labels=False,
                draw_confidence_interval=False,
            )

            ax.set_title(
                f"{y_label} as a function of {x_label}, "
                f"grouped by {group_col} (n={total_n})"
            )

        else:
            (
                x_series,
                y_series,
                x_label,
                y_label,
                plot_data,
            ) = clean_xy(
                data,
                x_col,
                y_col,
                log_x_enabled,
                log_y_enabled,
                label=(
                    label_col
                    if label_enabled
                    else None
                ),
            )

            ax.set_title(
                f"{y_label} as a function of {x_label} "
                f"(n={len(plot_data)})"
            )

            if chart_type == "Plot":
                ax.plot(
                    x_series,
                    y_series,
                    label=y_label,
                )

            elif chart_type == "Scatter":
                ax.scatter(
                    x_series,
                    y_series,
                    label=y_label,
                )

            handle_options(
                data,
                label_name="All data",
                draw_regression=True,
                draw_labels=True,
                draw_confidence_interval=True,
            )

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        handles, legend_labels = ax.get_legend_handles_labels()

        if handles:
            ax.legend(
                facecolor="white",
                edgecolor="black",
                framealpha=1,
            )

        if correlation_lines:
            report_fig, report_ax = plt.subplots(
                figsize=(10, 6)
            )

            report_ax.axis("off")

            report_ax.text(
                0.01,
                0.98,
                "\n".join(correlation_lines),
                ha="left",
                va="top",
                fontsize=11,
                family="monospace",
                transform=report_ax.transAxes,
            )

            report_fig.suptitle(
                "Statistical Report",
                fontweight="bold",
            )

        plt.show()

    except Exception as e:
        sg.popup_error(
            "Unable to generate the chart.\n\n"
            f"Reason:\n{e}\n\n"
            "Possible causes:\n"
            "• Log10 can only be applied to numeric data.\n"
            "• Dates and text cannot be log-transformed.\n"
            "• The selected columns may contain incompatible "
            "data types."
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
                [sg.Text("Note: To apply settings you must Save & Exit.")],
                [
                    sg.Text("Theme:", pad=(0, 30)),
                    sg.Combo(
                        values=AVAILABLE_THEMES,
                        key="-SETTINGS-THEME-",
                        default_value=selected_theme,
                        readonly=True,
                    ),
                ],
                [
                    sg.Text("Font Size:", pad=(0, 30)),
                    sg.Combo(
                        key="-SETTINGS-FONTSIZE-",
                        values=FONT_SIZES,
                        default_value=selected_font_size,
                        readonly=True,
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