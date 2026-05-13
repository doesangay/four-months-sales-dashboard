"""
Sales Intelligence Dashboard — Online Games Revenue Analytics.

"""

import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit import runtime
from streamlit.web import cli as stcli

# ==========================================
# 1. DATA ENGINE & COLOUR CONFIG
# ==========================================

COLOR_MAP = {
    "Crossword":          "#00e5ff",
    "Bingo":              "#df20df",
    "Spin the Wheel":     "#f1c40f",
    "Race 6":             "#10d25f",
    "Spin Roulette":      "#38b284",
    "Crossword Paradise": "#f06277",
    "Terdrup":            "#8b5cf6",
    "Pick 3":             "#3b82f6",
    "Lotto":              "#a855f7",
    "Pick 4":             "#f97316",
    "Free Roll":          "#0ea5e9",
}

DARK_TEMPLATE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0"),
)

GRID_COLOR = "rgba(255,255,255,0.06)"
LEGEND_H   = dict(orientation="h", y=-0.22)


# ==========================================
# 2. DATA LOADER
# ==========================================

@st.cache_data
def load_data():
    """Load and pre-process the sales CSV; return (DataFrame, product_col_list)."""
    try:
        df = pd.read_csv("Online sales1.csv")
    except FileNotFoundError:
        return pd.DataFrame(), []

    product_cols = list(COLOR_MAP.keys())

    for col in product_cols + ["Wagers/sales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "").str.replace('"', ""),
                errors="coerce",
            )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Date"]).sort_values("Date")

    df["Month"]     = df["Date"].dt.month_name()
    df["MonthNum"]  = df["Date"].dt.month
    df["Week"]      = df["Date"].dt.isocalendar().week.astype(int)
    df["DayOfWeek"] = df["Date"].dt.day_name()
    df["Year"]      = df["Date"].dt.year
    df["Total Sales"] = df[product_cols].sum(axis=1)

    return df, product_cols


# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def growth_badge(val):
    """Return a formatted MoM growth string with sign."""
    if val > 0:
        return f"+{val:.1f}%"
    if val < 0:
        return f"{val:.1f}%"
    return "0.0%"


def compute_mom_growth(df, product_cols):
    """
    Compute month-over-month growth for every product and Total Sales.

    Returns (growth_dict, (prev_label, last_label)) or (None, None) if
    fewer than two months of data are available.
    """
    monthly = (
        df.groupby(["Year", "MonthNum"])[product_cols + ["Total Sales"]]
        .sum()
        .reset_index()
        .sort_values(["Year", "MonthNum"])
    )
    if len(monthly) < 2:
        return None, None

    last = monthly.iloc[-1]
    prev = monthly.iloc[-2]
    growth = {}
    for col in product_cols + ["Total Sales"]:
        if prev[col] != 0:
            growth[col] = ((last[col] - prev[col]) / prev[col]) * 100
        else:
            growth[col] = 0.0

    last_label = f"{int(last['Year'])} M{int(last['MonthNum'])}"
    prev_label = f"{int(prev['Year'])} M{int(prev['MonthNum'])}"
    return growth, (prev_label, last_label)


def get_product_stats(df, product_cols):
    """
    Build a per-product summary DataFrame with total revenue, average
    daily revenue, peak day, peak date, and market share.
    """
    total_all = df[product_cols].sum().sum()
    stats = []
    for p in product_cols:
        s     = df[p].dropna()
        total = s.sum()
        avg   = s.mean()
        peak  = s.max()

        peak_dates = df.loc[df[p] == peak, "Date"].values
        peak_date_str = (
            str(pd.to_datetime(peak_dates[0]).date())
            if len(peak_dates) > 0
            else "N/A"
        )
        share = (total / total_all * 100) if total_all > 0 else 0
        stats.append(
            {
                "Product":        p,
                "Total Revenue":  total,
                "Avg Daily":      avg,
                "Peak Day":       peak,
                "Peak Date":      peak_date_str,
                "Market Share %": share,
                "Color":          COLOR_MAP[p],
            }
        )
    return (
        pd.DataFrame(stats)
        .sort_values("Total Revenue", ascending=False)
        .reset_index(drop=True)
    )


# ==========================================
# 4. CSS
# ==========================================

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* ── KPI card ── */
.metric-card {
    background: linear-gradient(145deg, #0b1629 0%, #111f3a 60%, #0d2040 100%);
    border: 1px solid rgba(0,229,255,0.12);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 10px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(0,229,255,0.5), transparent);
}
.metric-card .label {
    font-size: 10px; color: #4a7fa5; text-transform: uppercase;
    letter-spacing: 1.8px; margin-bottom: 6px; font-weight: 600;
}
.metric-card .value {
    font-size: 24px; font-weight: 800; color: #f0f8ff;
    font-family: 'JetBrains Mono', monospace; letter-spacing: -0.5px;
}
.metric-card .delta-pos { font-size: 12px; color: #10d25f; margin-top: 4px; font-weight: 600; }
.metric-card .delta-neg { font-size: 12px; color: #ef4444; margin-top: 4px; font-weight: 600; }
.metric-card .delta-neu { font-size: 12px; color: #4a7fa5; margin-top: 4px; }

/* ── Product scorecard ── */
.product-scorecard {
    background: linear-gradient(145deg, #0b1629 0%, #111f3a 100%);
    border-radius: 14px;
    padding: 18px 20px;
    border-left: 3px solid var(--accent);
    margin-bottom: 12px;
    border-top: 1px solid rgba(255,255,255,0.05);
    border-right: 1px solid rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}
.product-scorecard::after {
    content: '';
    position: absolute; top: 0; right: 0;
    width: 60px; height: 60px;
    background: radial-gradient(circle at top right, var(--accent) 0%, transparent 70%);
    opacity: 0.08;
}
.scorecard-name  { font-size: 13px; font-weight: 700; color: #e2eaf4; margin-bottom: 8px; }
.scorecard-total {
    font-size: 22px; font-weight: 800; color: #f0f8ff;
    font-family: 'JetBrains Mono', monospace;
}
.scorecard-sub   { font-size: 11px; color: #4a7fa5; margin-top: 3px; }
.scorecard-share { font-size: 12px; font-weight: 600; color: #7faac4; margin-top: 6px; }
.rank-badge {
    display: inline-block;
    background: rgba(0,229,255,0.1);
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 5px;
    padding: 1px 7px; font-size: 10px; color: #00e5ff;
    margin-right: 7px; font-family: 'JetBrains Mono', monospace;
}

/* ── Section headers ── */
.section-header {
    font-size: 18px; font-weight: 700; color: #c8dff0;
    margin: 28px 0 16px 0; padding-bottom: 10px;
    border-bottom: 1px solid rgba(0,229,255,0.15);
    letter-spacing: -0.3px;
}

/* ── Tabs ── */
div[data-testid="stTabs"] button {
    font-family: 'Outfit', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
}

/* ── Dashboard header ── */
.dash-header {
    padding: 20px 0 24px 0;
    border-bottom: 1px solid rgba(0,229,255,0.1);
    margin-bottom: 24px;
}
.dash-title {
    font-size: 30px; font-weight: 800; color: #f0f8ff;
    letter-spacing: -1px; line-height: 1.1;
}
.dash-subtitle {
    font-size: 13px; color: #4a7fa5; margin-top: 6px; font-weight: 400;
}
.accent-dot {
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; background: #00e5ff;
    margin-right: 10px; box-shadow: 0 0 10px #00e5ff;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}
</style>
"""


# ==========================================
# 5. CHART HELPERS
# ==========================================

def _base_layout(**overrides):
    """Return a merged DARK_TEMPLATE dict with optional overrides."""
    layout = {**DARK_TEMPLATE}
    layout.update(overrides)
    return layout


def chart_ranking(df_f, active_cols):
    """Horizontal bar chart of total revenue per product."""
    totals = (
        df_f[active_cols].sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    totals.columns = ["Product", "Sales"]

    fig = go.Figure(
        go.Bar(
            x=totals["Sales"],
            y=totals["Product"],
            orientation="h",
            marker=dict(
                color=[COLOR_MAP.get(p) for p in totals["Product"]],
                opacity=0.9,
                line=dict(width=0),
            ),
            text=totals["Sales"],
            texttemplate="$%{text:,.0f}",
            textposition="outside",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(
        title="Total Revenue Ranking",
        **_base_layout(height=420),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False),
        margin=dict(l=10, r=110, t=44, b=10),
    )
    return fig


def chart_pie(df_f, active_cols):
    """Donut chart of revenue market share."""
    pie_data = df_f[active_cols].sum().reset_index()
    pie_data.columns = ["Product", "Sales"]

    fig = px.pie(
        pie_data,
        names="Product",
        values="Sales",
        color="Product",
        color_discrete_map=COLOR_MAP,
        hole=0.55,
        title="Revenue Market Share",
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=10,
    )
    fig.update_layout(
        **_base_layout(height=420, showlegend=False),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


def chart_deep_dive(df_f, product):
    """Bar + two moving-average lines for a single product."""
    deep = df_f[["Date", product]].copy()
    deep["7DMA"]  = deep[product].rolling(7).mean()
    deep["30DMA"] = deep[product].rolling(30).mean()
    color = COLOR_MAP[product]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=deep["Date"],
            y=deep[product],
            name="Daily Revenue",
            marker_color=color,
            opacity=0.45,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=deep["Date"],
            y=deep["7DMA"],
            name="7-Day MA",
            line=dict(color="#f1c40f", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=deep["Date"],
            y=deep["30DMA"],
            name="30-Day MA",
            line=dict(color="#ef4444", width=2, dash="dot"),
        )
    )
    fig.update_layout(
        title=f"{product} — Daily Revenue + Moving Averages",
        **_base_layout(height=380),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def chart_stacked_area(df_f, active_cols):
    """Stacked area chart — all products over time."""
    fig = go.Figure()
    for p in active_cols:
        fig.add_trace(
            go.Scatter(
                x=df_f["Date"],
                y=df_f[p],
                name=p,
                stackgroup="one",
                line=dict(width=0.5, color=COLOR_MAP[p]),
                fillcolor=COLOR_MAP[p],
                opacity=0.75,
            )
        )
    fig.update_layout(
        title="Cumulative Daily Revenue — All Products (Stacked)",
        **_base_layout(height=400),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        legend=LEGEND_H,
        margin=dict(l=10, r=10, t=44, b=70),
    )
    return fig


def chart_monthly_grouped(df_f, active_cols):
    """Grouped monthly bar chart."""
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    monthly = df_f.groupby("Month")[active_cols].sum().reset_index()
    monthly["_sort"] = monthly["Month"].apply(
        lambda x: month_order.index(x) if x in month_order else 99
    )
    monthly = monthly.sort_values("_sort").drop(columns="_sort")
    melted  = monthly.melt(id_vars="Month", var_name="Product", value_name="Sales")

    fig = px.bar(
        melted,
        x="Month",
        y="Sales",
        color="Product",
        barmode="group",
        title="Monthly Revenue per Product",
        color_discrete_map=COLOR_MAP,
    )
    fig.update_layout(
        **_base_layout(height=380),
        legend=LEGEND_H,
        margin=dict(l=10, r=10, t=44, b=90),
    )
    return fig


def chart_trend_total(df_f):
    """Total revenue trend with 7-day and 30-day moving averages."""
    df_f = df_f.copy()
    df_f["7DMA"]  = df_f["Total Sales"].rolling(7).mean()
    df_f["30DMA"] = df_f["Total Sales"].rolling(30).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_f["Date"],
            y=df_f["Total Sales"],
            name="Daily Total",
            mode="lines",
            line=dict(color="rgba(255,255,255,0.15)", width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_f["Date"],
            y=df_f["7DMA"],
            name="7-Day MA",
            line=dict(color="#00e5ff", width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_f["Date"],
            y=df_f["30DMA"],
            name="30-Day MA",
            line=dict(color="#f1c40f", width=2.5, dash="dash"),
        )
    )
    fig.update_layout(
        title="Total Revenue Trend",
        **_base_layout(height=350),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=52, b=10),
    )
    return fig


def chart_dow(df_f, active_cols):
    """Stacked bar by day of week."""
    dow_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    dow_data   = (
        df_f.groupby("DayOfWeek")[active_cols]
        .sum()
        .reindex(dow_order)
        .reset_index()
    )
    dow_melted = dow_data.melt(
        id_vars="DayOfWeek", var_name="Product", value_name="Sales"
    )
    fig = px.bar(
        dow_melted,
        x="DayOfWeek",
        y="Sales",
        color="Product",
        barmode="stack",
        title="Revenue by Day of Week",
        color_discrete_map=COLOR_MAP,
    )
    fig.update_layout(
        **_base_layout(height=350),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        legend=LEGEND_H,
        margin=dict(l=10, r=10, t=44, b=90),
    )
    return fig


def chart_correlation(df_f, active_cols):
    """Product sales correlation heatmap."""
    corr = df_f[active_cols].corr()
    fig  = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        title="Product Sales Correlation Matrix",
        aspect="auto",
    )
    fig.update_layout(
        **_base_layout(height=450),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


def chart_weekly(df_f, active_cols):
    """Weekly rolling revenue per product."""
    weekly = (
        df_f.groupby(["Year", "Week"])[active_cols]
        .sum()
        .reset_index()
    )
    weekly["PeriodLabel"] = (
        weekly["Year"].astype(str)
        + "-W"
        + weekly["Week"].astype(str).str.zfill(2)
    )
    melted_w = weekly.melt(
        id_vars="PeriodLabel",
        value_vars=active_cols,
        var_name="Product",
        value_name="Sales",
    )
    fig = px.line(
        melted_w,
        x="PeriodLabel",
        y="Sales",
        color="Product",
        title="Weekly Revenue Breakdown",
        color_discrete_map=COLOR_MAP,
    )
    fig.update_layout(
        **_base_layout(height=380),
        xaxis=dict(showgrid=False, tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        legend=LEGEND_H,
        margin=dict(l=10, r=10, t=44, b=110),
    )
    return fig


def chart_monthly_champions(df_f, active_cols):
    """Bar chart showing the top-earning product each month."""
    monthly_by_product = df_f.groupby("Month")[active_cols].sum()
    monthly_winner     = monthly_by_product.idxmax(axis=1).reset_index()
    monthly_winner.columns = ["Month", "Top Product"]
    monthly_winner["Revenue"] = [
        monthly_by_product.loc[row["Month"], row["Top Product"]]
        for _, row in monthly_winner.iterrows()
    ]
    fig = px.bar(
        monthly_winner,
        x="Month",
        y="Revenue",
        color="Top Product",
        text="Top Product",
        title="Monthly Champion Product",
        color_discrete_map=COLOR_MAP,
    )
    fig.update_layout(
        **_base_layout(height=370, showlegend=False),
        margin=dict(l=10, r=10, t=44, b=70),
    )
    return fig


def chart_pareto(df_f, active_cols):
    """Pareto revenue concentration chart."""
    sorted_rev = df_f[active_cols].sum().sort_values(ascending=False)
    cumulative = (sorted_rev.cumsum() / sorted_rev.sum() * 100).reset_index()
    cumulative.columns = ["Product", "Cumulative %"]
    cumulative["Revenue"] = sorted_rev.values

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=cumulative["Product"],
            y=cumulative["Revenue"],
            name="Revenue",
            marker_color=[COLOR_MAP.get(p, "#fff") for p in cumulative["Product"]],
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=cumulative["Product"],
            y=cumulative["Cumulative %"],
            name="Cumulative %",
            line=dict(color="#f1c40f", width=2.5),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Pareto Revenue Analysis",
        **_base_layout(height=370),
        legend=dict(orientation="h", y=1.14),
        margin=dict(l=10, r=10, t=52, b=70),
    )
    fig.update_yaxes(title_text="Revenue",       secondary_y=False)
    fig.update_yaxes(title_text="Cumulative %",  secondary_y=True, range=[0, 110])
    return fig


def chart_efficiency_matrix(stats_df):
    """Bubble scatter: avg daily vs total revenue, sized by market share."""
    fig = px.scatter(
        stats_df,
        x="Avg Daily",
        y="Total Revenue",
        size="Market Share %",
        color="Product",
        text="Product",
        title="Product Efficiency Matrix (bubble = market share)",
        color_discrete_map={
            row["Product"]: row["Color"] for _, row in stats_df.iterrows()
        },
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(
        **_base_layout(height=420, showlegend=False),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


# ==========================================
# 6. MAIN DASHBOARD
# ==========================================

def main():
    """Entry point — builds and renders the full Streamlit dashboard."""
    st.set_page_config(
        page_title="AI Sales Dashboard",
        layout="wide",
        page_icon="📈",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    df, product_cols = load_data()

    if df.empty:
        st.error(
            "Data file not found. "
            "Please ensure 'Online sales1.csv' is in the working directory."
        )
        return

    # ── SIDEBAR ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (df["Date"].dt.date >= start_date)
                & (df["Date"].dt.date <= end_date)
            ]

        selected_products = st.multiselect(
            "Focus Products",
            options=product_cols,
            default=product_cols,
            help="Select products to include in all charts",
        )
        if not selected_products:
            selected_products = product_cols

        st.markdown("---")
        st.markdown("### Quick Stats")
        st.caption(f"Range: {df['Date'].min().date()} → {df['Date'].max().date()}")
        st.caption(f"Total days: {df['Date'].nunique()}")
        st.caption(f"Products tracked: {len(selected_products)}")

    df_f         = df.copy()
    active_cols  = [p for p in product_cols if p in selected_products]

    # ── HEADER ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="dash-header">
            <div class="dash-title">
                <span class="accent-dot"></span>
                AI Sales Intelligence
            </div>
            <div class="dash-subtitle">
                Real-time product performance analysis across all game categories
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI ROW ───────────────────────────────────────────────────────────
    mom_growth, mom_labels = compute_mom_growth(df_f, active_cols)
    total_rev     = df_f[active_cols].sum().sum()
    best_product  = df_f[active_cols].sum().idxmax()
    worst_product = df_f[active_cols].sum().idxmin()
    avg_daily     = df_f["Total Sales"].mean()
    active_days   = df_f["Date"].nunique()
    total_mom     = mom_growth["Total Sales"] if mom_growth else 0.0

    def _delta_cls(val):
        if val > 0:
            return "delta-pos"
        if val < 0:
            return "delta-neg"
        return "delta-neu"

    def _arrow(val):
        if val > 0:
            return "&#8593;"
        if val < 0:
            return "&#8595;"
        return "—"

    kpi_data = [
        (
            "Total Revenue",
            f"${total_rev:,.0f}",
            total_mom,
            "MoM",
        ),
        (
            "Best Performer",
            best_product,
            None,
            f"${df_f[best_product].sum():,.0f} total",
        ),
        (
            "Avg Daily Revenue",
            f"${avg_daily:,.0f}",
            None,
            f"Over {active_days} days",
        ),
        (
            "Needs Attention",
            worst_product,
            None,
            f"${df_f[worst_product].sum():,.0f} total",
        ),
        (
            "Products Tracked",
            str(len(active_cols)),
            None,
            f"{active_cols[0]} leading",
        ),
    ]

    for col, (label, value, delta, sub) in zip(st.columns(5), kpi_data):
        if delta is not None:
            dc    = _delta_cls(delta)
            arrow = _arrow(delta)
            delta_html = (
                f'<div class="{dc}">'
                f'{arrow} {growth_badge(delta)} {sub}'
                f"</div>"
            )
        else:
            delta_html = f'<div class="delta-neu">{sub}</div>'

        col.markdown(
            f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                {delta_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "📊 All Products",
            "🔭 Overview",
            "📈 Trends",
            "🧠 Market Intelligence",
            "🤖 AI Analyze",
            "🗃️ Raw Data",
        ]
    )

    stats_df = get_product_stats(df_f, active_cols)

    # ── TAB 1: ALL PRODUCTS ──────────────────────────────────────────────
    with tab1:
        st.markdown(
            '<div class="section-header">Individual Product Scorecards</div>',
            unsafe_allow_html=True,
        )
        rows = [active_cols[i : i + 3] for i in range(0, len(active_cols), 3)]
        for row in rows:
            cols_row = st.columns(3)
            for idx, product in enumerate(row):
                p_stats  = stats_df[stats_df["Product"] == product].iloc[0]
                rank_val = (
                    stats_df.index[stats_df["Product"] == product].tolist()[0] + 1
                )
                color   = COLOR_MAP[product]
                mom_val = (
                    mom_growth[product]
                    if mom_growth and product in mom_growth
                    else 0.0
                )
                mom_str   = growth_badge(mom_val)
                mom_color = "#10d25f" if mom_val >= 0 else "#ef4444"

                with cols_row[idx]:
                    st.markdown(
                        f"""
                        <div class="product-scorecard" style="--accent: {color};">
                            <div class="scorecard-name">
                                <span class="rank-badge">#{rank_val}</span>{product}
                            </div>
                            <div class="scorecard-total">
                                ${p_stats['Total Revenue']:,.0f}
                            </div>
                            <div class="scorecard-sub">
                                Avg/Day: ${p_stats['Avg Daily']:,.0f}
                            </div>
                            <div class="scorecard-sub">
                                Peak: ${p_stats['Peak Day']:,.0f}
                                on {p_stats['Peak Date']}
                            </div>
                            <div class="scorecard-share">
                                Share: {p_stats['Market Share %']:.1f}%
                                &nbsp;|&nbsp;
                                <span style="color:{mom_color};">
                                    MoM {mom_str}
                                </span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown(
            '<div class="section-header">Revenue Ranking & Market Share</div>',
            unsafe_allow_html=True,
        )
        col_rank, col_pie = st.columns([3, 2])
        with col_rank:
            st.plotly_chart(
                chart_ranking(df_f, active_cols), use_container_width=True
            )
        with col_pie:
            st.plotly_chart(
                chart_pie(df_f, active_cols), use_container_width=True
            )

        st.markdown(
            '<div class="section-header">Individual Product Deep Dive</div>',
            unsafe_allow_html=True,
        )
        selected_deep = st.selectbox("Select a product to deep dive", active_cols)
        if selected_deep:
            st.plotly_chart(
                chart_deep_dive(df_f, selected_deep), use_container_width=True
            )
            d_stats = stats_df[stats_df["Product"] == selected_deep].iloc[0]
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Revenue",   f"${d_stats['Total Revenue']:,.0f}")
            s2.metric("Avg Daily",       f"${d_stats['Avg Daily']:,.0f}")
            s3.metric("Peak Single Day", f"${d_stats['Peak Day']:,.0f}")
            s4.metric("Market Share",    f"{d_stats['Market Share %']:.2f}%")

    # ── TAB 2: OVERVIEW ──────────────────────────────────────────────────
    with tab2:
        st.markdown(
            '<div class="section-header">Overall Performance Snapshot</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_stacked_area(df_f, active_cols), use_container_width=True
        )

        col_bar, col_tbl = st.columns([2, 1])
        with col_bar:
            st.plotly_chart(
                chart_monthly_grouped(df_f, active_cols), use_container_width=True
            )
        with col_tbl:
            st.markdown("**Product Revenue Summary**")
            summary_tbl = stats_df[
                ["Product", "Total Revenue", "Market Share %", "Avg Daily"]
            ].copy()
            summary_tbl["Total Revenue"]  = summary_tbl["Total Revenue"].apply(
                lambda x: f"${x:,.0f}"
            )
            summary_tbl["Market Share %"] = summary_tbl["Market Share %"].apply(
                lambda x: f"{x:.1f}%"
            )
            summary_tbl["Avg Daily"]       = summary_tbl["Avg Daily"].apply(
                lambda x: f"${x:,.0f}"
            )
            st.dataframe(summary_tbl, use_container_width=True, hide_index=True)

    # ── TAB 3: TRENDS ────────────────────────────────────────────────────
    with tab3:
        st.markdown(
            '<div class="section-header">Trends & Time-Series Analysis</div>',
            unsafe_allow_html=True,
        )
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.plotly_chart(chart_trend_total(df_f), use_container_width=True)
        with t_col2:
            st.plotly_chart(
                chart_dow(df_f, active_cols), use_container_width=True
            )

        st.markdown(
            '<div class="section-header">Product Correlation Heatmap</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_correlation(df_f, active_cols), use_container_width=True
        )

        st.markdown(
            '<div class="section-header">Weekly Rolling Revenue per Product</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_weekly(df_f, active_cols), use_container_width=True
        )

    # ── TAB 4: MARKET INTELLIGENCE ───────────────────────────────────────
    with tab4:
        st.markdown(
            '<div class="section-header">Competitive Market Intelligence</div>',
            unsafe_allow_html=True,
        )
        mi_col1, mi_col2 = st.columns(2)
        with mi_col1:
            st.plotly_chart(
                chart_monthly_champions(df_f, active_cols),
                use_container_width=True,
            )
        with mi_col2:
            st.plotly_chart(
                chart_pareto(df_f, active_cols), use_container_width=True
            )

        st.markdown(
            '<div class="section-header">Month-over-Month Growth Table</div>',
            unsafe_allow_html=True,
        )
        if mom_growth and mom_labels:
            prev_m = int(mom_labels[0].split("M")[1])
            last_m = int(mom_labels[1].split("M")[1])
            growth_rows = []
            for p in active_cols:
                g = mom_growth.get(p, 0.0)
                rev_prev = df_f[df_f["MonthNum"] == prev_m][p].sum()
                rev_last = df_f[df_f["MonthNum"] == last_m][p].sum()
                growth_rows.append(
                    {
                        "Product":                    p,
                        f"Revenue ({mom_labels[0]})": f"${rev_prev:,.0f}",
                        f"Revenue ({mom_labels[1]})": f"${rev_last:,.0f}",
                        "MoM Growth":                 growth_badge(g),
                        "Direction": (
                            "▲ UP" if g > 0 else ("▼ DOWN" if g < 0 else "— FLAT")
                        ),
                    }
                )
            st.dataframe(
                pd.DataFrame(growth_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Not enough monthly data to compute MoM growth.")

        st.markdown(
            '<div class="section-header">'
            "Efficiency Matrix — Avg Daily vs Total Revenue"
            "</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_efficiency_matrix(stats_df), use_container_width=True
        )

    # ── TAB 5: AI ANALYZE ────────────────────────────────────────────────
    with tab5:
        st.markdown(
            '<div class="section-header">AI Search & Analyze</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "Ask me anything about your sales data. "
            "Try: *'Compare Lotto and Bingo'*, *'Show monthly'*, "
            "*'Trend analysis'*, *'Risk'*, *'Best day'*"
        )

        user_query = st.text_input(
            "Your question:",
            placeholder=(
                "e.g., Compare Lotto and Bingo | "
                "Monthly breakdown | Trend | Worst performers"
            ),
        )

        if user_query:
            q = user_query.lower()
            st.write("### Insight Result")

            if "compare" in q or " vs " in q:
                found = [p for p in active_cols if p.lower() in q]
                if len(found) >= 2:
                    p1, p2 = found[0], found[1]
                    diff   = df_f[p1].sum() - df_f[p2].sum()
                    winner = p1 if diff > 0 else p2
                    st.info(
                        f"Comparison: **{p1}** vs **{p2}**. "
                        f"**{winner}** leads by **${abs(diff):,.0f}**."
                    )
                    fig_c = px.line(
                        df_f,
                        x="Date",
                        y=[p1, p2],
                        title=f"Timeline: {p1} vs {p2}",
                        color_discrete_map={
                            p1: COLOR_MAP[p1],
                            p2: COLOR_MAP[p2],
                        },
                    )
                    fig_c.update_layout(**DARK_TEMPLATE)
                    st.plotly_chart(fig_c, use_container_width=True)
                    a1, a2 = st.columns(2)
                    a1.metric(
                        p1,
                        f"${df_f[p1].sum():,.0f}",
                        f"Avg/day ${df_f[p1].mean():,.0f}",
                    )
                    a2.metric(
                        p2,
                        f"${df_f[p2].sum():,.0f}",
                        f"Avg/day ${df_f[p2].mean():,.0f}",
                    )
                else:
                    st.warning(
                        "Mention at least two valid product names "
                        "(e.g., 'Compare Lotto and Bingo')."
                    )

            elif "month" in q:
                month_order = [
                    "January", "February", "March", "April",
                    "May", "June", "July", "August",
                    "September", "October", "November", "December",
                ]
                month_data = df_f.groupby("Month")[active_cols].sum().reset_index()
                month_data["Total"]   = month_data[active_cols].sum(axis=1)
                month_data["_sort"]   = month_data["Month"].apply(
                    lambda x: month_order.index(x) if x in month_order else 99
                )
                month_data = month_data.sort_values("_sort").drop(columns="_sort")
                best_month = month_data.loc[
                    month_data["Total"].idxmax(), "Month"
                ]
                st.success(
                    f"Your strongest month overall is **{best_month}**."
                )
                melted = month_data.drop(columns="Total").melt(id_vars="Month")
                fig_m  = px.bar(
                    melted,
                    x="Month",
                    y="value",
                    color="variable",
                    barmode="group",
                    title="Monthly Product Breakdown",
                    color_discrete_map=COLOR_MAP,
                )
                fig_m.update_layout(**DARK_TEMPLATE)
                st.plotly_chart(fig_m, use_container_width=True)

            elif "trend" in q or "moving average" in q:
                st.info(
                    "Showing 7-day moving average to smooth daily fluctuations."
                )
                st.plotly_chart(
                    chart_trend_total(df_f), use_container_width=True
                )

            elif any(kw in q for kw in ("risk", "worst", "low", "weak")):
                bottom_3 = (
                    df_f[active_cols].sum().sort_values().head(3)
                )
                st.warning(
                    f"Low performers: **{', '.join(bottom_3.index)}**"
                )
                fig_risk = px.pie(
                    names=bottom_3.index,
                    values=bottom_3.values,
                    hole=0.4,
                    title="Revenue Share of Lowest Performers",
                    color_discrete_sequence=["#ff4b4b", "#ff7676", "#ffb1b1"],
                )
                st.plotly_chart(fig_risk, use_container_width=True)

            elif any(kw in q for kw in ("best day", "top day", "highest day")):
                best_row = df_f.loc[df_f["Total Sales"].idxmax()]
                best_date = str(best_row["Date"].date())
                best_total = best_row["Total Sales"]
                st.success(
                    f"Best single day: **{best_date}** "
                    f"with **${best_total:,.0f}** in total sales."
                )
                best_detail = (
                    best_row[active_cols]
                    .sort_values(ascending=False)
                    .reset_index()
                )
                best_detail.columns = ["Product", "Revenue"]
                fig_bd = px.bar(
                    best_detail,
                    x="Product",
                    y="Revenue",
                    title=f"Revenue Breakdown on {best_date}",
                    color="Product",
                    color_discrete_map=COLOR_MAP,
                )
                fig_bd.update_layout(**DARK_TEMPLATE)
                st.plotly_chart(fig_bd, use_container_width=True)

            elif any(p.lower() in q for p in active_cols):
                found_p  = next(p for p in active_cols if p.lower() in q)
                p_stats  = stats_df[stats_df["Product"] == found_p].iloc[0]
                st.info(f"Showing full analysis for **{found_p}**")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Revenue", f"${p_stats['Total Revenue']:,.0f}")
                m2.metric("Avg Daily",     f"${p_stats['Avg Daily']:,.0f}")
                m3.metric("Peak Day",      f"${p_stats['Peak Day']:,.0f}")
                m4.metric("Market Share",  f"{p_stats['Market Share %']:.2f}%")
                fig_sp = px.line(
                    df_f,
                    x="Date",
                    y=found_p,
                    title=f"{found_p} Daily Revenue",
                    color_discrete_sequence=[COLOR_MAP[found_p]],
                )
                fig_sp.update_layout(**DARK_TEMPLATE)
                st.plotly_chart(fig_sp, use_container_width=True)

            else:
                st.write(
                    "I'm not sure how to answer that yet. Try: "
                    "**'compare X and Y'**, **'monthly sales'**, **'trend'**, "
                    "**'risk'**, **'best day'**, or a product name."
                )

    # ── TAB 6: RAW DATA ──────────────────────────────────────────────────
    with tab6:
        st.markdown(
            '<div class="section-header">Raw Data Explorer</div>',
            unsafe_allow_html=True,
        )
        search_term = st.text_input(
            "Filter by date (YYYY-MM-DD) or any value:",
            placeholder="e.g. 2024-01",
        )
        display_df = df_f.copy()
        if search_term:
            mask = (
                display_df.astype(str)
                .apply(lambda col: col.str.contains(search_term, case=False))
                .any(axis=1)
            )
            display_df = display_df[mask]

        st.caption(f"Showing {len(display_df):,} rows")
        st.dataframe(display_df, use_container_width=True)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇  Download Filtered Data as CSV",
            data=csv,
            file_name="sales_export.csv",
            mime="text/csv",
        )


# ==========================================
# 7. EXECUTION
# ==========================================

if __name__ == "__main__":
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
