#!/usr/bin/env python3
"""
Chamber Sensor Data Dashboard (Render-ready)
"""

import os
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from pathlib import Path
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data-cac-12-02.xlsx"
CLEANED_DATA_FILE = BASE_DIR / "cleaned_dataset.xlsx"

APP_TITLE = "Chamber Sensor Dashboard"

VARIABLE_INFO = {
    "t": {"name": "Temperature", "unit": "°C"},
    "rh": {"name": "Relative Humidity", "unit": "%"},
    "co2": {"name": "CO₂", "unit": "%"},
    "o2": {"name": "O₂", "unit": "%"},
    "n2": {"name": "N₂", "unit": "%"},
}

NUM_CHAMBERS = 30
CHAMBERS = [f"c{str(i).zfill(2)}" for i in range(1, NUM_CHAMBERS + 1)]

# =============================================================================
# DATA
# =============================================================================

def load_data():
    if CLEANED_DATA_FILE.exists():
        file_path = CLEANED_DATA_FILE
    elif DATA_FILE.exists():
        file_path = DATA_FILE
    else:
        raise FileNotFoundError("No data file found")

    df = pd.read_excel(file_path)

    if "tcol" in df.columns:
        df["tcol"] = pd.to_datetime(df["tcol"])

    return df


def calculate_n2(df):
    for chamber in CHAMBERS:
        co2 = f"{chamber}_co2_pv"
        o2 = f"{chamber}_o2_pv"
        n2 = f"{chamber}_n2_pv"

        if co2 in df.columns and o2 in df.columns:
            df[n2] = 100 - df[co2] - df[o2]

    return df


def get_available_chambers(df):
    return sorted([col.replace("_t_pv", "") for col in df.columns if col.endswith("_t_pv")])


# =============================================================================
# APP
# =============================================================================

df = load_data()
df = calculate_n2(df)
available_chambers = get_available_chambers(df)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H1(APP_TITLE),

    dcc.Dropdown(
        id="chamber-selector",
        options=[{"label": c, "value": c} for c in available_chambers],
        value=["c01"],
        multi=True
    ),

    dcc.Dropdown(
        id="variable-selector",
        options=[{"label": v, "value": v} for v in VARIABLE_INFO.keys()],
        value=["t"],
        multi=True
    ),

    dcc.Graph(id="main-plot")
])


# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    Output("main-plot", "figure"),
    Input("chamber-selector", "value"),
    Input("variable-selector", "value")
)
def update_plot(chambers, variables):

    if not chambers or not variables:
        return go.Figure()

    fig = go.Figure()

    for ch in chambers:
        for var in variables:
            col = f"{ch}_{var}_pv"
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["tcol"],
                    y=df[col],
                    mode="lines",
                    name=f"{ch}-{var}"
                ))

    fig.update_layout(template="plotly_white")
    return fig


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)