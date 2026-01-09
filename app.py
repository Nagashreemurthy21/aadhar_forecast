import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re

st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
html, body, .stApp { background-color: #fdf3e7 !important; }
header, footer { visibility: hidden; height: 0; }
.section-header {
    background: #fff4e6;
    padding: 14px 22px;
    border-radius: 18px;
    font-weight: 600;
    font-size: 20px;
    margin: 16px auto 8px auto;
    width: fit-content;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    with open("aadhaar_data.csv", "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    clean = [l for l in lines if l.strip() and not l.startswith("#") and l.count(",") >= 3]
    df = pd.read_csv(io.StringIO("".join(clean)), sep=",", engine="python")
    df.columns = df.columns.str.lower().str.strip()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

df = load_data()

def valid_text(x):
    return isinstance(x, str) and not re.fullmatch(r"\d+", x)

if "state" in df.columns:
    df = df[df["state"].apply(valid_text)]
if "district" in df.columns:
    df = df[df["district"].apply(valid_text)]

numeric_cols = df.select_dtypes("number").columns.tolist()
service_col = numeric_cols[0]

with st.sidebar:
    st.markdown("## 🔍 Filter Data")

    if "date" in df.columns:
        years = sorted(df["date"].dt.year.dropna().unique())
        if len(years) > 1:
            year_range = st.slider("Year Range", years[0], years[-1], (years[0], years[-1]))
        else:
            year_range = (years[0], years[0])
            st.info(f"Only one year: {years[0]}")

    states = sorted(df["state"].dropna().unique())
    cities = sorted(df["district"].dropna().unique())

    state_filter = st.multiselect("Select State", states, default=states[:3])
    city_filter = st.multiselect("Select City", cities, default=cities[:5])

    top_n = st.slider("Top cities", 5, 15, 8)

# APPLY FILTERS
filtered = df.copy()

if "date" in filtered.columns:
    filtered = filtered[(filtered["date"].dt.year >= year_range[0]) & (filtered["date"].dt.year <= year_range[1])]

if state_filter:
    filtered = filtered[filtered["state"].isin(state_filter)]

if city_filter:
    filtered = filtered[filtered["district"].isin(city_filter)]

st.write(f"Showing {len(filtered):,} rows after filtering.")

if filtered.empty:
    st.error("No data matches your conditions.")
    st.stop()

# METRICS
total = filtered[service_col].sum()
avg = filtered[service_col].mean()

st.markdown("<h1 style='text-align:center;'>Aadhaar Service Demand Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Interactive analytics with clean cream UI</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.metric("Total Demand", f"{int(total):,}")
c2.metric("Average Demand", f"{int(avg):,}")

# PIE
st.markdown('<div class="section-header">🍑 Distribution by City</div>', unsafe_allow_html=True)

pie = (
    filtered.groupby("district")[service_col]
    .sum()
    .reset_index()
    .rename(columns={"district": "City", service_col: "Demand"})
    .sort_values("Demand", ascending=False)
)

if pie.empty:
    st.info("No data for pie.")
else:
    fig_pie = px.pie(
        pie.head(top_n),
        names="City",
        values="Demand",
        hole=0.45,
        color_discrete_sequence=["#F2C9AC","#E8B89A","#DDA57C","#C18C5D","#A47551","#8A5E3B"]
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# BAR
st.markdown('<div class="section-header">🏙 Top Cities by Demand</div>', unsafe_allow_html=True)

bar = pie.head(top_n)

fig_bar = px.bar(
    bar,
    x="City",
    y="Demand",
    color="Demand",
    color_continuous_scale=["#FFF1E1","#F2C9AC","#E8B89A","#DDA57C","#C18C5D","#A47551","#8A5E3B"]
)
st.plotly_chart(fig_bar, use_container_width=True)

# HEATMAP
st.markdown('<div class="section-header">🔥 Demand Heatmap (City × Year)</div>', unsafe_allow_html=True)

filtered["Year"] = filtered["date"].dt.year
heat = filtered.groupby(["district", "Year"])[service_col].sum().reset_index()

if heat.empty:
    st.info("No data for heatmap.")
else:
    pivot = heat.pivot(index="district", columns="Year", values=service_col).fillna(0)

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=["#FFF1E1","#F2C9AC","#E8B89A","#DDA57C","#C18C5D","#A47551","#8A5E3B"],
        aspect="auto"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with st.expander("📄 Filtered Data"):
    st.dataframe(filtered)
