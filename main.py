import PySimpleGUI as sg
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from cycler import cycler
import base64
import cairosvg
import json
from scipy.stats import pearsonr, spearmanr

import os
from pathlib import Path

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
    state_values.update(get_checkbox_values(window))
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
        "figure.dpi": 300,
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

checked = b"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"
unchecked = b"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"
water_drop = "PCFET0NUWVBFIHN2ZyBQVUJMSUMgIi0vL1czQy8vRFREIFNWRyAxLjEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkIj4KPCEtLSBVcGxvYWRlZCB0bzogU1ZHIFJlcG8sIHd3dy5zdmdyZXBvLmNvbSwgVHJhbnNmb3JtZWQgYnk6IFNWRyBSZXBvIE1peGVyIFRvb2xzIC0tPgo8c3ZnIGZpbGw9IiM5OWMxZjEiIHdpZHRoPSI4MDBweCIgaGVpZ2h0PSI4MDBweCIgdmlld0JveD0iMCAwIDIyIDIyIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGlkPSJtZW1vcnktd2F0ZXIiPgoNPGcgaWQ9IlNWR1JlcG9fYmdDYXJyaWVyIiBzdHJva2Utd2lkdGg9IjAiLz4KDTxnIGlkPSJTVkdSZXBvX3RyYWNlckNhcnJpZXIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgoNPGcgaWQ9IlNWR1JlcG9faWNvbkNhcnJpZXIiPgoNPHBhdGggZD0iTTE0LDIxSDhWMjBINlYxOUg1VjE4SDRWMTZIM1YxM0g0VjExSDVWOUg2VjdIN1Y2SDhWNEg5VjNIMTBWMUgxMlYzSDEzVjRIMTRWNkgxNVY3SDE2VjlIMTdWMTFIMThWMTNIMTlWMTZIMThWMThIMTdWMTlIMTZWMjBIMTRaIi8+Cg08L2c+Cg08L3N2Zz4="


def svg_base64_to_png_bytes(svg_base64: str, width=50, height=50) -> bytes:
    # Handles both raw base64 and data URLs like:
    # data:image/svg+xml;base64,...
    if "," in svg_base64:
        svg_base64 = svg_base64.split(",", 1)[1]

    svg_bytes = base64.b64decode(svg_base64)

    return cairosvg.svg2png(
        bytestring=svg_bytes,
        output_width=width,
        output_height=height,
    )


png_bytes = svg_base64_to_png_bytes(water_drop, 60, 60)

CUSTOM_CHECKBOX_KEYS = [
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


# Every ordinary user-editable control whose value should survive a restart.
# The image-based checkboxes are persisted separately via CUSTOM_CHECKBOX_KEYS.
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
]

# Retrieve state if available
state = load_state()

sg.set_options(font=("Arial", state.get("-SETTINGS-FONTSIZE-", 12)))
sg.theme(state.get("-SETTINGS-THEME-", sg.theme()))

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

def fancy_checkbox(text, key, default=None):
    if default is None:
        default = state.get(key, False)

    return [
        sg.Image(
            checked if default else unchecked,
            key=("-CB-IMAGE-", key),
            metadata=default,
            enable_events=True,
            pad=((0, 6), 0),
        ),
        sg.Text(
            text,
            key=("-CB-TEXT-", key),
            enable_events=True,
            pad=((0, 20), 0),
        ),
    ]


def get_checkbox_values(window):
    return {key: window[("-CB-IMAGE-", key)].metadata for key in CUSTOM_CHECKBOX_KEYS}


def read_excel(path, sheet=None):
    if sheet:
        return pd.read_excel(path, sheet_name=sheet)
    return pd.read_excel(path)


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
                        r, p = pearsonr(
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
                        rho, p = spearmanr(
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

    def restored_choice(key, options, fallback=""):
        saved_value = state.get(key, fallback)
        return saved_value if saved_value in options else fallback

    default_x = number_columns[0] if number_columns else ""
    default_y = number_columns[1] if len(number_columns) > 1 else ""
    default_third_number = number_columns[2] if len(number_columns) > 2 else ""
    default_third_column = columns[2] if len(columns) > 2 else ""

    window["-SIMPLE-X-"].update(
        values=number_columns,
        value=restored_choice("-SIMPLE-X-", number_columns, default_x),
    )
    window["-SIMPLE-Y-"].update(
        values=number_columns,
        value=restored_choice("-SIMPLE-Y-", number_columns, default_y),
    )

    window["-ADVANCED-X-"].update(
        values=number_columns,
        value=restored_choice("-ADVANCED-X-", number_columns, default_x),
    )
    window["-ADVANCED-Y-"].update(
        values=number_columns,
        value=restored_choice("-ADVANCED-Y-", number_columns, default_y),
    )
    group_col = restored_choice(
        "-ADVANCED-GROUP-COL-", columns, default_third_column
    )
    window["-ADVANCED-GROUP-COL-"].update(
        values=columns,
        value=group_col,
    )
    window["-ADVANCED-LABEL-COL-"].update(
        values=columns,
        value=restored_choice(
            "-ADVANCED-LABEL-COL-", columns, default_third_column
        ),
    )
    window["-ADVANCED-UPPER-LIMIT-COL-"].update(
        values=number_columns,
        value=restored_choice(
            "-ADVANCED-UPPER-LIMIT-COL-", number_columns, default_third_number
        ),
    )
    window["-ADVANCED-LOWER-LIMIT-COL-"].update(
        values=number_columns,
        value=restored_choice(
            "-ADVANCED-LOWER-LIMIT-COL-", number_columns, default_third_number
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
                sg.Input(key="FileSelect", default_text=state.get("FileSelect", None)),
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
            values=["Plot", "Scatter"],
            default_value=state.get("-SIMPLE-TYPE-", "Scatter"),
            readonly=True,
        ),
        sg.Button("Plot", key="-SIMPLE-CHART-"),
    ],
    [
        *fancy_checkbox("Log10 x", "-SIMPLE-LOGX-"),
        *fancy_checkbox("Log10 y", "-SIMPLE-LOGY-"),
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
            values=["Plot", "Scatter"],
            default_value=state.get("-ADVANCED-TYPE-", "Scatter"),
            readonly=True,
        ),
        sg.Button("Plot", key="-ADVANCED-CHART-"),
    ], #choose scatter or plot
    [
        *fancy_checkbox("Log10 x", "-ADVANCED-LOGX-"),
        *fancy_checkbox("Log10 y", "-ADVANCED-LOGY-"),
        *fancy_checkbox("Linear Regression", "-ADVANCED-LINEAR-REGRESSION-"),
        *fancy_checkbox("Pearson Correlation", "-ADVANCED-PEARSON-"),
        *fancy_checkbox("Spearman Correlation", "-ADVANCED-SPEARMAN-"),
    ], #data options; log, correlation, linear regression
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Grouping:", font=("Arial", 14, "bold"), pad=(0, 30))],
    [
        *fancy_checkbox("Activate Grouping", "-ADVANCED-GROUP?-"),
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
        *fancy_checkbox("Activate Labels", "-ADVANCED-LABELS?-"),
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
        *fancy_checkbox("Enable season shading", "-ADVANCED-SHADING-"),
    ], #enable season shading
    [
        sg.Text("Dry season starts:"),
        sg.Combo(
            values=list(range(1, 13)),
            default_value=state.get("-DRY-START-MONTH-", 1),
            key="-DRY-START-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
        sg.Text("Wet season starts:"),
        sg.Combo(
            values=list(range(1, 13)),
            default_value=state.get("-WET-START-MONTH-", 5),
            key="-WET-START-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
        sg.Text("Dry season starts again:"),
        sg.Combo(
            values=list(range(1, 13)),
            default_value=state.get("-DRY-RESTART-MONTH-", 11),
            key="-DRY-RESTART-MONTH-",
            readonly=True,
            size=(5, 1),
        ),
    ], #season options
    [
        sg.Text("Dry season color:"),
        sg.Input(
            state.get("-DRY-COLOR-", "orange"),
            key="-DRY-COLOR-",
            size=(12, 1),
        ),
        sg.ColorChooserButton("Choose", target="-DRY-COLOR-"),
    ], #dry color
    [
        sg.Text("Wet season color:"),
        sg.Input(
            state.get("-WET-COLOR-", "blue"),
            key="-WET-COLOR-",
            size=(12, 1),
        ),
        sg.ColorChooserButton("Choose", target="-WET-COLOR-"),
    ], #wet color
    [sg.HSep(pad=(0, 30))],
    [sg.Text("Confidence Intervals:", pad=(0, 30), font=("Arial", 14, "bold"))],
    [
        *fancy_checkbox("Enable confidence intervals", "-ADVANCED-CONFIDENCE-INTERVALS-"),
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
                        values=sg.theme_list(),
                        key="-SETTINGS-THEME-",
                        default_value=state.get("-SETTINGS-THEME-", sg.theme()),
                    ),
                ],
                [
                    sg.Text("Font Size:", pad=(0, 30)),
                    sg.Combo(
                        key="-SETTINGS-FONTSIZE-",
                        values=[10, 11, 12, 13, 14, 15, 16, 17, 18],
                        default_value=state.get("-SETTINGS-FONTSIZE-", 12),
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
        sg.Image(png_bytes, size=(60, 60)),
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

        meta = read_excel(
            path=values["FileSelect"],
            sheet=meta_sheet_name,
        )
        data = read_excel(
            path=values["FileSelect"],
            sheet=data_sheet_name,
        )

        window["-README-GROUP-"].update(visible=True)
        window["-README-NAME-"].update(
            values=meta.columns.tolist(), value=state.get("-README-NAME-", "")
        )
        window["-README-UNIT-"].update(
            values=meta.columns.tolist(), value=state.get("-README-UNIT-", "")
        )
    if event == "Read":
        try:
            excel = pd.ExcelFile(values["FileSelect"])
            window["SheetSelect"].update(
                values=excel.sheet_names,
                value=state.get("SheetSelect", ""),
            )
            window["-README-SHEET-"].update(
                values=excel.sheet_names, value=state.get("-README-SHEET-", "")
            )
            window["-SELECT-SHEET-"].update(visible=True)
        except Exception as e:
            sg.popup_error(f"Could not read Excel file:\n{e}")

    if event == "-START-":
        try:
            name_col = values["-README-NAME-"]
            unit_col = values["-README-UNIT-"]

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

    if isinstance(event, tuple) and event[0] in ("-CB-IMAGE-", "-CB-TEXT-"):
        checkbox_key = event[1]
        image_key = ("-CB-IMAGE-", checkbox_key)

        window[image_key].metadata = not window[image_key].metadata
        window[image_key].update(checked if window[image_key].metadata else unchecked)

    if event == "-SIMPLE-CHART-":
        values.update(get_checkbox_values(window))
        simple_chart(data, values, meta_dict)

    if event == "-ADVANCED-CHART-":
        values.update(get_checkbox_values(window))
        advanced_chart(data, values, meta_dict)

window.close()