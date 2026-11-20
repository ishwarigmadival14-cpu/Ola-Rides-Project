"""Ola Ride Insights - Streamlit app.

Run:  streamlit run app/streamlit_app.py
Tabs mirror the Power BI pages (Overall, Vehicle Type, Revenue, Cancellation, Ratings) and add a SQL Explorer
and an embedded Power BI report. Set POWERBI_EMBED_URL (env var or Streamlit secret) to the report's
"Publish to web" / embed URL to enable the embed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sql_utils import DB_FILE, connect_readonly, load_queries, run_sql  # noqa: E402

YELLOW, BLACK = "#C6D32B", "#1A1A1A"
PALETTE = [BLACK, "#C6D32B", "#6B7280", "#F59E0B", "#10B981", "#3B82F6", "#EF4444"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

st.set_page_config(page_title="Ola Ride Insights", page_icon="🚖", layout="wide")


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    with connect_readonly() as conn:
        df = pd.read_sql_query("SELECT * FROM ola_rides", conn, parse_dates=["booking_date"])
    return df


@st.cache_data(show_spinner=False)
def cached_query(sql: str) -> pd.DataFrame:
    return run_sql(sql)


def kpi_row(df: pd.DataFrame) -> None:
    ok = df[df["booking_status"] == "Success"]
    cols = st.columns(6)
    cols[0].metric("Total bookings", f"{len(df):,}")
    cols[1].metric("Success rate", f"{100 * df['is_success'].mean():.1f}%" if len(df) else "-")
    cols[2].metric("Revenue", f"{ok['booking_value'].sum():,.0f}")
    cols[3].metric("Avg distance (km)", f"{ok['ride_distance'].mean():.1f}" if len(ok) else "-")
    cols[4].metric("Avg customer rating", f"{ok['customer_rating'].mean():.2f}" if len(ok) else "-")
    cols[5].metric("Avg driver rating", f"{ok['driver_rating'].mean():.2f}" if len(ok) else "-")


def style(fig):
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    return fig


def page_overall(df):
    daily = df.groupby("booking_date").size().reset_index(name="bookings")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(style(px.line(daily, x="booking_date", y="bookings", markers=True,
                                  title="Ride volume over time", color_discrete_sequence=[BLACK])),
                    use_container_width=True)
    status = df["booking_status"].value_counts().reset_index()
    c2.plotly_chart(style(px.pie(status, names="booking_status", values="count", hole=0.5,
                                 title="Booking status breakdown", color_discrete_sequence=PALETTE)),
                    use_container_width=True)
    hourly = df.groupby("booking_hour").size().reset_index(name="bookings")
    st.plotly_chart(style(px.bar(hourly, x="booking_hour", y="bookings", title="Demand by hour of day",
                                 color_discrete_sequence=[YELLOW])), use_container_width=True)


def page_vehicle(df):
    top = (df.groupby("vehicle_type")["ride_distance"].sum().sort_values(ascending=False).head(5)
           .reset_index())
    c1, c2 = st.columns(2)
    c1.plotly_chart(style(px.bar(top, x="vehicle_type", y="ride_distance", text_auto=".3s",
                                 title="Top 5 vehicle types by total ride distance (km)",
                                 color_discrete_sequence=[BLACK])), use_container_width=True)
    avg = df.groupby("vehicle_type")["ride_distance"].mean().sort_values().reset_index()
    c2.plotly_chart(style(px.bar(avg, x="ride_distance", y="vehicle_type", orientation="h",
                                 title="Average ride distance (km)", color_discrete_sequence=[YELLOW])),
                    use_container_width=True)


def page_revenue(df):
    ok = df[df["booking_status"] == "Success"]
    c1, c2 = st.columns(2)
    pay = ok.groupby("payment_method")["booking_value"].sum().reset_index()
    c1.plotly_chart(style(px.pie(pay, names="payment_method", values="booking_value", hole=0.5,
                                 title="Revenue by payment method", color_discrete_sequence=PALETTE)),
                    use_container_width=True)
    cust = ok.groupby("customer_id")["booking_value"].sum().sort_values(ascending=False).head(5).reset_index()
    c2.plotly_chart(style(px.bar(cust, x="customer_id", y="booking_value", text_auto=".0f",
                                 title="Top 5 customers by total booking value",
                                 color_discrete_sequence=[BLACK])), use_container_width=True)
    daily = df.groupby("booking_date")["ride_distance"].sum().reset_index()
    st.plotly_chart(style(px.bar(daily, x="booking_date", y="ride_distance",
                                 title="Ride distance per day (km)", color_discrete_sequence=[YELLOW])),
                    use_container_width=True)
    st.plotly_chart(style(px.box(df.dropna(subset=["ride_distance"]), x="day_name", y="ride_distance",
                                 category_orders={"day_name": DAY_ORDER},
                                 title="Ride distance distribution by weekday",
                                 color_discrete_sequence=[BLACK])), use_container_width=True)


def page_cancellation(df):
    c1, c2 = st.columns(2)
    for col, who, label in [(c1, "Customer", "customers"), (c2, "Driver", "drivers")]:
        d = df[df["cancelled_by"] == who]["cancel_reason"].value_counts().reset_index()
        col.plotly_chart(style(px.bar(d, x="count", y="cancel_reason", orientation="h",
                                      title=f"Cancellation reasons - {label}",
                                      color_discrete_sequence=[YELLOW if who == "Customer" else BLACK])
                               .update_yaxes(categoryorder="total ascending")), use_container_width=True)
    inc = df[df["is_incomplete"] == 1]["incomplete_reason"].value_counts().reset_index()
    st.plotly_chart(style(px.bar(inc, x="incomplete_reason", y="count", title="Incomplete ride reasons",
                                 color_discrete_sequence=[BLACK])), use_container_width=True)


def page_ratings(df):
    ok = df[df["booking_status"] == "Success"]
    c1, c2 = st.columns(2)
    c1.plotly_chart(style(px.histogram(ok, x="driver_rating", nbins=20, title="Driver ratings distribution",
                                       color_discrete_sequence=[BLACK])), use_container_width=True)
    c2.plotly_chart(style(px.histogram(ok, x="customer_rating", nbins=20, title="Customer ratings distribution",
                                       color_discrete_sequence=[YELLOW])), use_container_width=True)
    avg = ok.groupby("vehicle_type")[["customer_rating", "driver_rating"]].mean().reset_index()
    avg = avg.melt("vehicle_type", var_name="rating_type", value_name="avg_rating")
    c3, c4 = st.columns(2)
    c3.plotly_chart(style(px.bar(avg, x="vehicle_type", y="avg_rating", color="rating_type", barmode="group",
                                 title="Average rating by vehicle type", color_discrete_sequence=[YELLOW, BLACK])
                          .update_yaxes(range=[1, 5])), use_container_width=True)
    c4.plotly_chart(style(px.density_heatmap(ok.dropna(subset=["customer_rating", "driver_rating"]),
                                             x="customer_rating", y="driver_rating", nbinsx=10, nbinsy=10,
                                             title="Customer vs driver rating",
                                             color_continuous_scale="YlOrBr")), use_container_width=True)


def page_sql():
    st.subheader("SQL Explorer")
    st.caption("Queries live in `sql/queries.sql`. Q1-Q10 are the required questions; B1-B10 are extra business queries.")
    queries = load_queries()
    labels = [f"{q['id']} - {q['title']}" for q in queries]
    choice = st.selectbox("Choose a query", labels)
    q = queries[labels.index(choice)]
    st.code(q["sql"], language="sql")
    result = cached_query(q["sql"])
    st.write(f"**{len(result):,} rows**")
    search = st.text_input("Filter rows (text search across all columns)")
    shown = result
    if search:
        mask = result.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        shown = result[mask]
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.download_button("Download result as CSV", shown.to_csv(index=False), f"{q['id']}.csv", "text/csv")

    with st.expander("Write your own SQL (read-only SELECT)"):
        sql = st.text_area("SQL", "SELECT vehicle_type, COUNT(*) AS rides FROM ola_rides GROUP BY vehicle_type", height=120)
        if st.button("Run query"):
            try:
                st.dataframe(run_sql(sql), use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001 - show any SQL error to the user
                st.error(str(exc))


def page_powerbi():
    st.subheader("Power BI report")
    try:
        default_url = os.environ.get("POWERBI_EMBED_URL") or st.secrets.get("POWERBI_EMBED_URL", "")
    except Exception:  # noqa: BLE001 - no secrets file configured
        default_url = os.environ.get("POWERBI_EMBED_URL", "")
    url = st.text_input("Power BI embed URL", value=default_url,
                        help="Power BI Service > File > Embed report > Publish to web (public) > copy the link")
    if url.startswith("https://app.powerbi.com/"):
        components.iframe(url, height=650, scrolling=True)
    else:
        st.info("Paste your published Power BI link above (or set `POWERBI_EMBED_URL`). "
                "Build steps are in `powerbi/POWERBI_GUIDE.md`.")


def main():
    st.title("🚖 Ola Ride Insights")
    if not DB_FILE.exists():
        st.error("Database not found. Run `make all` (or the pipeline commands in README.md) first.")
        st.stop()
    data = load_data()

    st.sidebar.header("Filters")
    dmin, dmax = data["booking_date"].min().date(), data["booking_date"].max().date()
    rng = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    vehicles = st.sidebar.multiselect("Vehicle type", sorted(data["vehicle_type"].unique()))
    statuses = st.sidebar.multiselect("Booking status", sorted(data["booking_status"].unique()))
    df = data
    if isinstance(rng, tuple) and len(rng) == 2:
        df = df[(df["booking_date"] >= pd.Timestamp(rng[0])) & (df["booking_date"] <= pd.Timestamp(rng[1]))]
    if vehicles:
        df = df[df["vehicle_type"].isin(vehicles)]
    if statuses:
        df = df[df["booking_status"].isin(statuses)]
    st.sidebar.caption(f"{len(df):,} of {len(data):,} bookings selected")
    if df.empty:
        st.warning("No data for the selected filters.")
        st.stop()

    kpi_row(df)
    tabs = st.tabs(["Overall", "Vehicle Type", "Revenue", "Cancellation", "Ratings", "SQL Explorer", "Power BI"])
    with tabs[0]:
        page_overall(df)
    with tabs[1]:
        page_vehicle(df)
    with tabs[2]:
        page_revenue(df)
    with tabs[3]:
        page_cancellation(df)
    with tabs[4]:
        page_ratings(df)
    with tabs[5]:
        page_sql()
    with tabs[6]:
        page_powerbi()


main()
