#!/usr/bin/env python3
"""
Chamber Sensor Data Dashboard
=============================

Interactive dashboard for visualizing chamber sensor data (temperature, humidity,
CO2, O2, N2) across 30 chambers over time.

Features:
- Multi-select chamber selector
- Multi-select variable selector
- Interactive time series plots with zoom/pan
- Responsive design for large datasets

Usage (local):
    python chamber_dashboard.py

Then open http://127.0.0.1:8050/ in your browser.

Deployment:
    Served via Gunicorn on Render. Entry point: chamber_dashboard:server

Author: Generated for CAC Log Analysis
Date: 2026-03-27
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

# =============================================================================
# CONFIGURATION
# =============================================================================

# File path configuration
# The dashboard looks for the data file in the same directory by default
DATA_FILE = "cleaned_dataset.xlsx"
# Alternative: use cleaned_dataset.xlsx if it exists
CLEANED_DATA_FILE = "cleaned_dataset.xlsx"

# Dashboard configuration
APP_TITLE = "Chamber Sensor Dashboard"

# Variable metadata for display
VARIABLE_INFO = {
    "t": {"name": "Temperature", "unit": "°C", "color": "#e74c3c"},
    "rh": {"name": "Relative Humidity", "unit": "%", "color": "#3498db"},
    "co2": {"name": "CO₂", "unit": "%", "color": "#2ecc71"},
    "o2": {"name": "O₂", "unit": "%", "color": "#9b59b6"},
    "n2": {"name": "N₂ (calculated)", "unit": "%", "color": "#f39c12"},
}

# Chamber configuration
NUM_CHAMBERS = 30
CHAMBERS = [f"c{str(i).zfill(2)}" for i in range(1, NUM_CHAMBERS + 1)]

# =============================================================================
# DATA LOADING AND PREPROCESSING
# =============================================================================


def load_data():
    """
    Load and preprocess the chamber sensor data.

    Returns:
        pd.DataFrame: Preprocessed dataframe with timestamp column and sensor data.
    """
    # On Render the working directory is the repo root; locally it's the script dir.
    # Checking both covers either case.
    base_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]

    file_path = None
    for base in base_dirs:
        cleaned = os.path.join(base, CLEANED_DATA_FILE)
        raw = os.path.join(base, DATA_FILE)
        if os.path.exists(cleaned):
            file_path = cleaned
            print(f"Loading cleaned data from: {cleaned}")
            break
        if os.path.exists(raw):
            file_path = raw
            print(f"Loading raw data from: {raw}")
            break

    if file_path is None:
        raise FileNotFoundError(
            f"Data file not found. Expected '{CLEANED_DATA_FILE}' or '{DATA_FILE}' "
            f"in {base_dirs}"
        )

    df = pd.read_excel(file_path)

    if "tcol" in df.columns:
        df["tcol"] = pd.to_datetime(df["tcol"])

    print(f"Loaded {len(df)} records from {df['tcol'].min()} to {df['tcol'].max()}")

    return df


def calculate_n2(df):
    """
    Calculate N2 (nitrogen) percentage from CO2 and O2.
    N2 = 100 - CO2 - O2
    """
    df = df.copy()
    for chamber in CHAMBERS:
        co2_col = f"{chamber}_co2_pv"
        o2_col = f"{chamber}_o2_pv"
        n2_col = f"{chamber}_n2_pv"
        if co2_col in df.columns and o2_col in df.columns:
            df[n2_col] = 100 - df[co2_col] - df[o2_col]
    return df


def get_available_chambers(df):
    """Get list of chambers available in the dataset."""
    chambers = []
    for col in df.columns:
        if col.endswith("_t_pv"):
            chamber = col.replace("_t_pv", "")
            chambers.append(chamber)
    return sorted(chambers)


# =============================================================================
# DASHBOARD LAYOUT
# =============================================================================


def create_layout(df):
    """Create the dashboard layout with all components."""
    available_chambers = get_available_chambers(df)

    layout = dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        html.H1(APP_TITLE, className="text-primary mb-2"),
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            # Data summary
            dbc.Row(
                [
                    dbc.Col(
                        html.P(
                            [
                                html.Strong("Data Range: "),
                                f"{df['tcol'].min().strftime('%Y-%m-%d %H:%M')} to "
                                f"{df['tcol'].max().strftime('%Y-%m-%d %H:%M')} ",
                                html.Strong(" | Records: "),
                                f"{len(df):,} ",
                                html.Strong(" | Chambers: "),
                                f"{len(available_chambers)}",
                            ],
                            className="text-muted",
                        ),
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            # Control panel
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Select Chambers:", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id="chamber-selector",
                                options=[
                                    {"label": f"Chamber {c.upper()}", "value": c}
                                    for c in available_chambers
                                ],
                                value=["c01"],
                                multi=True,
                                placeholder="Select chambers to display...",
                                className="mb-3",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Select Variables:", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id="variable-selector",
                                options=[
                                    {
                                        "label": f"{VARIABLE_INFO[var]['name']} ({VARIABLE_INFO[var]['unit']})",
                                        "value": var,
                                    }
                                    for var in ["t", "rh", "co2", "o2", "n2"]
                                ],
                                value=["t", "rh"],
                                multi=True,
                                placeholder="Select variables to display...",
                                className="mb-3",
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            # Quick select buttons
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.ButtonGroup(
                                [
                                    dbc.Button("All Chambers", id="btn-all-chambers", size="sm", outline=True),
                                    dbc.Button("Clear Chambers", id="btn-clear-chambers", size="sm", outline=True),
                                    dbc.Button("All Variables", id="btn-all-variables", size="sm", outline=True),
                                    dbc.Button("Clear Variables", id="btn-clear-variables", size="sm", outline=True),
                                ],
                                className="mb-3",
                            ),
                        ],
                        width=12,
                    ),
                ],
            ),
            # Time range selector
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Time Range:", className="fw-bold mb-2"),
                            dcc.DatePickerRange(
                                id="date-range",
                                min_date_allowed=df["tcol"].min().date(),
                                max_date_allowed=df["tcol"].max().date(),
                                start_date=df["tcol"].min().date(),
                                end_date=df["tcol"].max().date(),
                                display_format="YYYY-MM-DD",
                                className="mb-3",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Aggregation:", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id="aggregation-selector",
                                options=[
                                    {"label": "Raw (hourly)", "value": "raw"},
                                    {"label": "Daily average", "value": "daily"},
                                    {"label": "Weekly average", "value": "weekly"},
                                ],
                                value="raw",
                                clearable=False,
                                className="mb-3",
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Y-axis Scale:", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id="yaxis-scale",
                                options=[
                                    {"label": "Independent", "value": "independent"},
                                    {"label": "Shared", "value": "shared"},
                                ],
                                value="independent",
                                clearable=False,
                                className="mb-3",
                            ),
                        ],
                        width=3,
                    ),
                ],
                className="mb-3",
            ),
            # Main plot area
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Loading(
                                id="loading-plot",
                                type="default",
                                children=[
                                    dcc.Graph(
                                        id="main-plot",
                                        config={
                                            "displayModeBar": True,
                                            "scrollZoom": True,
                                            "displaylogo": False,
                                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                        },
                                        style={"height": "70vh"},
                                    ),
                                ],
                            ),
                        ],
                        width=12,
                    ),
                ],
            ),
            # Statistics table
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Summary Statistics", className="mt-4 mb-3"),
                            html.Div(id="stats-table"),
                        ],
                        width=12,
                    ),
                ],
                className="mt-3",
            ),
            # Footer
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Hr(),
                            html.P(
                                [
                                    "Chamber Sensor Dashboard | ",
                                    "Data: ",
                                    html.Span(id="data-file-name", children=DATA_FILE),
                                    " | ",
                                    "Use mouse wheel to zoom, double-click to reset.",
                                ],
                                className="text-muted text-center",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mt-4",
            ),
        ],
        fluid=True,
        className="p-4",
    )

    return layout


# =============================================================================
# CALLBACKS
# =============================================================================


def register_callbacks(app, df):
    """Register all dashboard callbacks."""

    @app.callback(
        [
            Output("chamber-selector", "value"),
            Output("variable-selector", "value"),
        ],
        [
            Input("btn-all-chambers", "n_clicks"),
            Input("btn-clear-chambers", "n_clicks"),
            Input("btn-all-variables", "n_clicks"),
            Input("btn-clear-variables", "n_clicks"),
        ],
        [
            State("chamber-selector", "value"),
            State("variable-selector", "value"),
        ],
    )
    def handle_quick_buttons(n_all_ch, n_clear_ch, n_all_var, n_clear_var, current_ch, current_var):
        ctx = callback_context  # ← fixed: imported directly from dash

        if not ctx.triggered:
            return current_ch, current_var

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        available_chambers = get_available_chambers(df)
        all_variables = ["t", "rh", "co2", "o2", "n2"]

        if button_id == "btn-all-chambers":
            return available_chambers, current_var
        elif button_id == "btn-clear-chambers":
            return [], current_var
        elif button_id == "btn-all-variables":
            return current_ch, all_variables
        elif button_id == "btn-clear-variables":
            return current_ch, []

        return current_ch, current_var

    @app.callback(
        [Output("main-plot", "figure"), Output("stats-table", "children")],
        [
            Input("chamber-selector", "value"),
            Input("variable-selector", "value"),
            Input("date-range", "start_date"),
            Input("date-range", "end_date"),
            Input("aggregation-selector", "value"),
            Input("yaxis-scale", "value"),
        ],
    )
    def update_plot(selected_chambers, selected_variables, start_date, end_date, aggregation, yaxis_scale):
        if not selected_chambers or not selected_variables:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="Select chambers and variables to visualize",
                xaxis={"title": "Time"},
                yaxis={"title": "Value"},
                template="plotly_white",
            )
            return empty_fig, html.P("No data selected.")

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + pd.Timedelta(hours=23, minutes=59)
        df_filtered = df[(df["tcol"] >= start_dt) & (df["tcol"] <= end_dt)].copy()

        if aggregation == "daily":
            df_filtered["date"] = df_filtered["tcol"].dt.date
            agg_dict = {}
            for chamber in selected_chambers:
                for var in selected_variables:
                    col_name = f"{chamber}_{var}_pv"
                    if col_name in df_filtered.columns:
                        agg_dict[col_name] = "mean"
            df_agg = df_filtered.groupby("date").agg(agg_dict).reset_index()
            df_agg["tcol"] = pd.to_datetime(df_agg["date"])
            df_plot = df_agg
        elif aggregation == "weekly":
            df_filtered["week"] = df_filtered["tcol"].dt.isocalendar().week
            df_filtered["year"] = df_filtered["tcol"].dt.year
            agg_dict = {}
            for chamber in selected_chambers:
                for var in selected_variables:
                    col_name = f"{chamber}_{var}_pv"
                    if col_name in df_filtered.columns:
                        agg_dict[col_name] = "mean"
            df_agg = df_filtered.groupby(["year", "week"]).agg(agg_dict).reset_index()
            df_agg["tcol"] = pd.to_datetime(
                df_agg["year"].astype(str)
                + "-W"
                + df_agg["week"].astype(str).str.zfill(2)
                + "-1",
                format="%Y-W%W-%w",
            )
            df_plot = df_agg
        else:
            df_plot = df_filtered

        chamber_colors = px.colors.qualitative.Plotly
        traces = []

        for var in selected_variables:
            var_info = VARIABLE_INFO.get(var, {"name": var, "unit": "", "color": "#888"})
            for ch_idx, chamber in enumerate(selected_chambers):
                col_name = f"{chamber}_{var}_pv"
                if col_name in df_plot.columns:
                    color = chamber_colors[ch_idx % len(chamber_colors)]
                    trace = go.Scatter(
                        x=df_plot["tcol"],
                        y=df_plot[col_name],
                        mode="lines",
                        name=f"{chamber.upper()} - {var_info['name']}",
                        line=dict(color=color, width=1.5),
                        legendgroup=f"{chamber}",
                        showlegend=True,
                        hovertemplate=(
                            f"<b>{chamber.upper()}</b><br>"
                            f"{var_info['name']}: %{{y:.2f}} {var_info['unit']}<br>"
                            f"Time: %{{x}}<extra></extra>"
                        ),
                    )
                    traces.append(trace)

        fig = go.Figure(data=traces)

        title_parts = []
        if len(selected_chambers) <= 5:
            title_parts.append(f"Chambers: {', '.join([c.upper() for c in selected_chambers])}")
        else:
            title_parts.append(f"Chambers: {len(selected_chambers)} selected")
        title_parts.append(f"Variables: {', '.join([VARIABLE_INFO[v]['name'] for v in selected_variables])}")

        fig.update_layout(
            title={"text": "<br>".join(title_parts), "x": 0.5, "xanchor": "center"},
            xaxis={"title": "Time", "rangeslider": {"visible": True}, "type": "date"},
            yaxis={"title": "Value"},
            template="plotly_white",
            hovermode="x unified",
            legend={"orientation": "v", "yanchor": "top", "y": 0.99, "xanchor": "left", "x": 1.02},
        )

        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(step="all", label="All"),
                ])
            )
        )

        stats_data = []
        for chamber in selected_chambers[:10]:
            for var in selected_variables:
                col_name = f"{chamber}_{var}_pv"
                if col_name in df_filtered.columns:
                    stats_data.append({
                        "Chamber": chamber.upper(),
                        "Variable": VARIABLE_INFO[var]["name"],
                        "Mean": f"{df_filtered[col_name].mean():.2f}",
                        "Std": f"{df_filtered[col_name].std():.2f}",
                        "Min": f"{df_filtered[col_name].min():.2f}",
                        "Max": f"{df_filtered[col_name].max():.2f}",
                    })

        if stats_data:
            stats_table = dbc.Table.from_dataframe(
                pd.DataFrame(stats_data),
                striped=True, bordered=True, hover=True, size="sm", className="mt-2",
            )
        else:
            stats_table = html.P("No statistics available.")

        return fig, stats_table


# =============================================================================
# APPLICATION FACTORY
# =============================================================================

def create_app():
    """Create and configure the Dash application."""
    print("Loading data...")
    df = load_data()
    print("Calculating N2 values...")
    df = calculate_n2(df)

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title=APP_TITLE,
    )

    # ─── REQUIRED FOR GUNICORN / RENDER ───────────────────────────────────────
    # Render (and any WSGI server) needs to import `server`, not `app`.
    # Gunicorn start command: gunicorn chamber_dashboard:server
    app.layout = create_layout(df)
    register_callbacks(app, df)

    return app


app = create_app()
server = app.server  # ← WSGI entry point for Gunicorn


# =============================================================================
# LOCAL DEV ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))  # Render injects PORT automatically
    print(f"\nDashboard ready! → http://127.0.0.1:{port}/")
    app.run(host="0.0.0.0", debug=False, port=port)
