import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re

st.set_page_config(layout="wide")

# -------------------- STYLE --------------------
st.markdown("""
<style>
.block-container { padding: 1.5rem 2.5rem !important; }
html, body, .stApp { background-color: #fdf3e7 !important; }
header, footer { visibility: hidden; }
.section-header {
    background: #fff4e6;
    padding: 12px 22px;
    border-radius: 14px;
    font-weight: 600;
    font-size: 20px;
    margin: 22px auto 12px auto;
    width: fit-content;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# -------------------- LOAD DATA --------------------
@st.cache_data(show_spinner=False)
def load_data():
    with open("aadhaar_data.csv", "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    clean = [l for l in lines if l.strip() and l.count(",") >= 2]
    df = pd.read_csv(io.StringIO("".join(clean)))
    df.columns = df.columns.str.lower().str.strip()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df

df = load_data()

# -------------------- CLEAN TEXT --------------------
def valid_text(x):
    return isinstance(x, str) and not re.fullmatch(r"\d+", x)

if "state" in df.columns:
    df = df[df["state"].apply(valid_text)]

if "district" in df.columns:
    df = df[df["district"].apply(valid_text)]

# -------------------- SERVICE COLUMN --------------------
numeric_cols = df.select_dtypes(include="number").columns.tolist()
if not numeric_cols:
    st.error("No numeric service column found")
    st.stop()

service_col = numeric_cols[0]

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.markdown("## 🔍 Filters")

    if "date" in df.columns:
        years = sorted(df["date"].dropna().dt.year.unique())
        year_range = (years[0], years[-1]) if years else None
    else:
        year_range = None

    states = sorted(df["state"].dropna().unique()) if "state" in df.columns else []
    state_filter = st.multiselect("State", states)

    # 🔑 Dynamic city binding based on selected state(s)
    if state_filter:
        cities = (
            df[df["state"].isin(state_filter)]["district"]
            .dropna()
            .unique()
        )
    else:
        cities = df["district"].dropna().unique()

    cities = sorted(cities)

    city_filter = st.multiselect("City", cities)


    top_n = st.slider("Top Cities (Charts)", 5, 15, 8)

# -------------------- APPLY FILTERS --------------------
filtered = df.copy()

if year_range and "date" in filtered.columns:
    filtered = filtered[
        (filtered["date"].dt.year >= year_range[0]) &
        (filtered["date"].dt.year <= year_range[1])
    ]

if state_filter:
    filtered = filtered[filtered["state"].isin(state_filter)]

if city_filter:
    filtered = filtered[filtered["district"].isin(city_filter)]

if filtered.empty:
    st.warning("No data for selected filters")
    st.stop()

# -------------------- METRICS --------------------
total = int(filtered[service_col].sum())
avg = int(filtered[service_col].mean())

st.markdown("<h1 style='text-align:center;'>Aadhaar Service Demand Dashboard</h1>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.metric("Total Demand", f"{total:,}")
c2.metric("Average Demand", f"{avg:,}")

# -------------------- CITY DISTRIBUTION --------------------
city_df = (
    filtered.groupby("district")[service_col]
    .sum()
    .reset_index()
    .rename(columns={"district": "City", service_col: "Demand"})
    .sort_values("Demand", ascending=False)
    .head(top_n)
)

st.markdown('<div class="section-header">City Distribution</div>', unsafe_allow_html=True)

fig_pie = px.pie(
    city_df,
    names="City",
    values="Demand",
    hole=0.45
)
fig_pie.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown('<div class="section-header">Top Cities</div>', unsafe_allow_html=True)

fig_bar = px.bar(
    city_df,
    x="City",
    y="Demand",
    color="Demand",
    height=420
)
fig_bar.update_layout(margin=dict(l=40, r=20, t=30, b=40))
st.plotly_chart(fig_bar, use_container_width=True)

# -------------------- IMPROVED HEATMAP --------------------
st.markdown('<div class="section-header">Demand Heatmap</div>', unsafe_allow_html=True)

if "date" in filtered.columns and filtered["district"].nunique() > 1:
    filtered["year"] = filtered["date"].dt.year

    heat_df = (
        filtered.groupby(["district", "year"])[service_col]
        .sum()
        .reset_index()
    )

    # LIMIT TO TOP 10 CITIES (IMPORTANT FOR UX)
    top_cities = (
        heat_df.groupby("district")[service_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .index
    )

    heat_df = heat_df[heat_df["district"].isin(top_cities)]

    pivot = heat_df.pivot(
        index="district",
        columns="year",
        values=service_col
    ).fillna(0)

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="YlOrRd",
        aspect="auto",
        height=120 + 40 * len(pivot)
    )

    fig_heat.update_layout(
        xaxis_title="Year",
        yaxis_title="City",
        margin=dict(l=120, r=20, t=30, b=40),
        coloraxis_colorbar=dict(title="Demand")
    )

    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("Heatmap requires multiple cities and valid date data.")

# -------------------- TABLE --------------------
with st.expander("📄 Filtered Data"):
    st.dataframe(filtered)
