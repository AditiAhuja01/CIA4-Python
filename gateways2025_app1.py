import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
import re
from collections import Counter

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GATEWAYS 2025 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS  — light mode, teal-orange palette, no symbols
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #004d40 0%, #00695c 100%);
}
[data-testid="stSidebar"] * { color: #e0f2f1 !important; }
[data-testid="stSidebar"] hr { border-color: #4db6ac !important; }

/* Let Streamlit handle background correctly */

.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 20px 14px 16px;
    box-shadow: 0 2px 10px rgba(0,77,64,.10);
    border-left: 5px solid;
    text-align: center;
}
.kpi-value { font-size: 1.9rem; font-weight: 700; margin: 4px 0 2px; }
.kpi-label { font-size: 0.76rem; color: #555; font-weight: 600;
             text-transform: uppercase; letter-spacing: .6px; }

.section-header {
    font-size: 1.05rem; font-weight: 700;
    color: #26a69a; margin: 4px 0 12px;
    padding-bottom: 5px;
    border-bottom: 2.5px solid #00897b;
}

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COLOR PALETTE  (teal + orange)
# ─────────────────────────────────────────────
MIXED      = ["#004d40","#e65100","#00897b","#f57c00","#26a69a","#fb8c00","#4db6ac"]
SEQ_TEAL   = "Teal"
SEQ_ORANGE = "Oranges"

# ─────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("C5-FestDataset_-_fest_dataset.csv")
    df.columns = df.columns.str.strip()
    df["Rating"]      = pd.to_numeric(df["Rating"],      errors="coerce")
    df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce")
    return df

df = load_data()

# ─────────────────────────────────────────────
# BUILD INDIA GEODATAFRAME (all states, no internet)
# ─────────────────────────────────────────────
@st.cache_resource
def build_india_gdf():
    import geopandas as gpd
    import os
    import zipfile
    
    zip_path = "maps-master.zip"
    extract_folder = "maps-master"
    shp_path = "maps-master/Districts/Census_2011/2011_Dist.shp"

    try:
        if os.path.exists(zip_path) and not os.path.exists(extract_folder):
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_folder)
        
        # Load District shapefile if available
        if os.path.exists(shp_path):
            gdf = gpd.read_file(shp_path)
            if 'ST_NM' in gdf.columns:
                gdf = gdf.rename(columns={'ST_NM': 'State'})
            if 'State' in gdf.columns:
                gdf['State'] = gdf['State'].replace({
                    'Andaman & Nicobar Island': 'Andaman and Nicobar Islands',
                    'Arunanchal Pradesh': 'Arunachal Pradesh',
                    'Dadara & Nagar Havelli': 'Dadra and Nagar Haveli and Daman and Diu',
                    'Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
                    'NCT of Delhi': 'Delhi',
                    'Jammu & Kashmir': 'Jammu and Kashmir',
                })
            return gdf
    except Exception:
        pass

    # Fallback to general state geojson
    if os.path.exists('india_states.geojson'):
        try:
            gdf = gpd.read_file('india_states.geojson')
            if 'ST_NM' in gdf.columns:
                gdf = gdf.rename(columns={'ST_NM': 'State'})
            elif 'name_1' in gdf.columns:
                gdf = gdf.rename(columns={'name_1': 'State'})
            if 'State' in gdf.columns:
                gdf['State'] = gdf['State'].replace({
                    'Andaman & Nicobar Island': 'Andaman and Nicobar Islands',
                    'Arunanchal Pradesh': 'Arunachal Pradesh',
                    'Dadara & Nagar Havelli': 'Dadra and Nagar Haveli and Daman and Diu',
                    'Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
                    'NCT of Delhi': 'Delhi',
                    'Jammu & Kashmir': 'Jammu and Kashmir',
                })
            return gdf
        except Exception:
            pass
            
    return gpd.GeoDataFrame({'State': [], 'geometry': []}, crs='EPSG:4326')

india_gdf = build_india_gdf()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## GATEWAYS 2025")
    st.markdown("**National Tech Fest Analytics**")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Overview", "Participation Trends", "Feedback and Ratings", "India State Map"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("### Filters")
    all_events = ["All Events"] + sorted(df["Event Name"].unique().tolist())
    sel_event  = st.selectbox("Event", all_events)
    all_states = ["All States"] + sorted(df["State"].unique().tolist())
    sel_state  = st.selectbox("State", all_states)
    rating_range = st.slider("Rating Range", 1, 5, (1, 5))
    st.markdown("---")
    st.caption("Built for GATEWAYS 2025 Organizing Team")

# Apply filters
fdf = df.copy()
if sel_event != "All Events":
    fdf = fdf[fdf["Event Name"] == sel_event]
if sel_state != "All States":
    fdf = fdf[fdf["State"] == sel_state]
fdf = fdf[fdf["Rating"].between(rating_range[0], rating_range[1])]

# ─────────────────────────────────────────────
# KPI helper
# ─────────────────────────────────────────────
def kpi(col_obj, value, label, color):
    col_obj.markdown(
        f"""<div class="kpi-card" style="border-left-color:{color}">
               <div class="kpi-value" style="color:{color}">{value}</div>
               <div class="kpi-label">{label}</div>
            </div>""",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# Shared plotly layout helper
# ─────────────────────────────────────────────
def clean_layout(fig, xlab="", ylab=""):
    fig.update_layout(
        font=dict(family="Inter", size=12),
        xaxis=dict(title=dict(text=xlab, font=dict(size=13))),
        yaxis=dict(title=dict(text=ylab, font=dict(size=13))),
        margin=dict(l=10, r=10, t=30, b=10),
        coloraxis_showscale=False,
    )
    return fig

# ═══════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ═══════════════════════════════════════════════
if page == "Overview":
    st.markdown("# GATEWAYS 2025 — Dashboard Overview")
    st.markdown("*National-level tech fest · Participant analytics for the organizing team*")
    st.markdown("---")

    k1, k2, k3, k4, k5 = st.columns(5)
    kpi(k1, len(fdf),                        "Total Participants", "#004d40")
    kpi(k2, fdf["College"].nunique(),         "Colleges",          "#00695c")
    kpi(k3, fdf["State"].nunique(),           "States",            "#e65100")
    kpi(k4, fdf["Event Name"].nunique(),      "Events",            "#f57c00")
    kpi(k5, f"Rs.{fdf['Amount Paid'].sum():,}", "Total Revenue",   "#00897b")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-header">Participants per Event</div>', unsafe_allow_html=True)
        ev = fdf["Event Name"].value_counts().reset_index()
        ev.columns = ["Event", "Participants"]
        fig = px.bar(ev, x="Participants", y="Event", orientation="h",
                     color="Participants", color_continuous_scale=SEQ_TEAL,
                     text="Participants", height=340)
        fig.update_traces(textposition="outside")
        clean_layout(fig, xlab="Number of Participants", ylab="Event")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Event Type Distribution</div>', unsafe_allow_html=True)
        et = fdf["Event Type"].value_counts().reset_index()
        et.columns = ["Event Type", "Count"]
        fig2 = px.pie(et, names="Event Type", values="Count",
                      color_discrete_sequence=MIXED, hole=0.45, height=340)
        fig2.update_traces(textinfo="label+percent", pull=[0.04]*len(et))
        fig2.update_layout(font=dict(family="Inter"),
                           margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="section-header">Rating Distribution</div>', unsafe_allow_html=True)
        rat = fdf["Rating"].value_counts().sort_index().reset_index()
        rat.columns = ["Rating (Stars)", "Count"]
        fig3 = px.bar(rat, x="Rating (Stars)", y="Count",
                      color="Count", color_continuous_scale=SEQ_ORANGE,
                      text="Count", height=300)
        fig3.update_traces(textposition="outside")
        clean_layout(fig3, xlab="Rating (Stars)", ylab="Number of Participants")
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        st.markdown('<div class="section-header">Revenue by Event</div>', unsafe_allow_html=True)
        rev = fdf.groupby("Event Name")["Amount Paid"].sum().reset_index()
        rev.columns = ["Event", "Revenue (Rs.)"]
        fig4 = px.bar(rev, x="Event", y="Revenue (Rs.)",
                      color="Revenue (Rs.)", color_continuous_scale=SEQ_TEAL,
                      text_auto=",.0f", height=300)
        clean_layout(fig4, xlab="Event", ylab="Revenue (Rs.)")
        fig4.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════
# PAGE 2 — PARTICIPATION TRENDS
# ═══════════════════════════════════════════════
elif page == "Participation Trends":
    st.markdown("# Participation Trends")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">State-wise Participant Count</div>', unsafe_allow_html=True)
        sc = fdf["State"].value_counts().reset_index()
        sc.columns = ["State", "Participants"]
        fig1 = px.bar(sc, x="State", y="Participants",
                      color="Participants", color_continuous_scale=SEQ_ORANGE,
                      text="Participants", height=380)
        fig1.update_traces(textposition="outside")
        clean_layout(fig1, xlab="State", ylab="Number of Participants")
        fig1.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Top 10 Colleges by Participation</div>', unsafe_allow_html=True)
        top_col = fdf["College"].value_counts().head(10).reset_index()
        top_col.columns = ["College", "Participants"]
        fig2 = px.bar(top_col, x="College", y="Participants",
                     color="Participants", color_continuous_scale=SEQ_TEAL,
                     text="Participants", height=380)
        fig2.update_traces(textposition="outside")
        clean_layout(fig2, xlab="College", ylab="Number of Participants")
        fig2.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)


    st.markdown('<div class="section-header">Event Registration Proportion</div>', unsafe_allow_html=True)
    ev_prop = fdf["Event Name"].value_counts().reset_index()
    ev_prop.columns = ["Event", "Registrations"]
    fig4 = px.pie(ev_prop, names="Event", values="Registrations", hole=0.4, 
                  color_discrete_sequence=MIXED, height=380)
    fig4.update_traces(textinfo="percent+label")
    fig4.update_layout(margin=dict(l=10,r=10,t=10,b=10), font=dict(family="Inter", size=12), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════
# PAGE 3 — FEEDBACK AND RATINGS
# ═══════════════════════════════════════════════
elif page == "Feedback and Ratings":
    st.markdown("# Participant Feedback and Ratings")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Average Rating by Event</div>', unsafe_allow_html=True)
        ar = fdf.groupby("Event Name")["Rating"].mean().reset_index()
        ar.columns = ["Event", "Average Rating"]
        ar["Average Rating"] = ar["Average Rating"].round(2)
        fig = px.bar(ar.sort_values("Average Rating", ascending=False),
                     x="Average Rating", y="Event", orientation="h",
                     color="Average Rating", color_continuous_scale=SEQ_TEAL,
                     text="Average Rating", range_x=[0, 5.5], height=320)
        fig.update_traces(textposition="outside")
        clean_layout(fig, xlab="Average Rating (out of 5)", ylab="Event")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Average Rating by State</div>', unsafe_allow_html=True)
        ar2 = fdf.groupby("State")["Rating"].mean().reset_index()
        ar2.columns = ["State", "Average Rating"]
        ar2["Average Rating"] = ar2["Average Rating"].round(2)
        fig2 = px.bar(ar2.sort_values("Average Rating", ascending=False),
                      x="State", y="Average Rating",
                      color="Average Rating", color_continuous_scale=SEQ_ORANGE,
                      text="Average Rating", range_y=[0, 5.5], height=320)
        fig2.update_traces(textposition="outside")
        clean_layout(fig2, xlab="State", ylab="Average Rating (out of 5)")
        fig2.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Top Feedback Themes</div>', unsafe_allow_html=True)
    fb = fdf["Feedback on Fest"].value_counts().head(12).reset_index()
    fb.columns = ["Feedback", "Count"]
    fig3 = px.bar(fb, x="Count", y="Feedback", orientation="h",
                  color="Count", color_continuous_scale=SEQ_TEAL,
                  text="Count", height=400)
    fig3.update_traces(textposition="outside")
    clean_layout(fig3, xlab="Number of Responses", ylab="Feedback Theme")
    st.plotly_chart(fig3, use_container_width=True)


    st.markdown('<div class="section-header">Feedback Explorer</div>', unsafe_allow_html=True)
    search = st.text_input("Search feedback by keyword", placeholder="e.g. creative, timing ...")
    view_df = fdf[["Student Name","College","State","Event Name","Rating","Feedback on Fest"]].copy()
    if search:
        view_df = view_df[view_df["Feedback on Fest"].str.contains(search, case=False, na=False)]
    st.dataframe(view_df.reset_index(drop=True), use_container_width=True, height=280)

# ═══════════════════════════════════════════════
# PAGE 4 — INDIA STATE MAP  (geopandas + matplotlib)
# ═══════════════════════════════════════════════
elif page == "India State Map":
    st.markdown("# State-wise Participation — India Map")
    st.markdown("---")

    state_cnt = df["State"].value_counts().reset_index()
    state_cnt.columns = ["State", "Participants"]

    merged = india_gdf.merge(state_cnt, on="State", how="left")
    merged["Participants"] = merged["Participants"].fillna(0)

    fig_map, ax = plt.subplots(1, 1, figsize=(14, 12))
    fig_map.patch.set_facecolor("none")
    ax.set_facecolor("none")

    # No-participant states in light grey
    no_part  = merged[merged["Participants"] == 0]
    has_part = merged[merged["Participants"] > 0]

    no_part.plot(ax=ax, color="#cfd8dc", edgecolor="white", linewidth=0.7)
    has_part.plot(
        column="Participants", ax=ax,
        cmap="YlGn", edgecolor="white", linewidth=0.9,
        legend=False,
    )

    # Colorbar
    vmin = merged["Participants"].min()
    vmax = merged["Participants"].max()
    sm   = plt.cm.ScalarMappable(cmap="YlGn", norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig_map.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Number of Participants", fontsize=12, color="#4db6ac", labelpad=10)
    cbar.ax.tick_params(labelsize=10, colors="#26a69a")

    # Short name map for labels
    short = {
        'Andhra Pradesh':'AP','Arunachal Pradesh':'Ar.Pr','Himachal Pradesh':'HP',
        'Jammu and Kashmir':'J&K','Madhya Pradesh':'MP','Tamil Nadu':'TN',
        'Uttar Pradesh':'UP','Uttarakhand':'UK','West Bengal':'WB',
        'Chhattisgarh':'CG','Maharashtra':'MH','Karnataka':'KA',
    }

    # Labels for states WITH participants
    try:
        labeled_has = has_part.dissolve(by="State").reset_index()
    except Exception:
        labeled_has = has_part.drop_duplicates(subset=["State"])

    for _, row in labeled_has.iterrows():
        cx = row.geometry.centroid.x
        cy = row.geometry.centroid.y
        nm  = short.get(row["State"], row["State"])
        cnt = int(row["Participants"])
        ax.text(cx, cy, f"{nm}\n{cnt}", fontsize=7.5, ha="center", va="center",
                color="#222", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.9, ec="none"))

    # Labels for states WITHOUT participants
    try:
        labeled_no = no_part.dissolve(by="State").reset_index()
    except Exception:
        labeled_no = no_part.drop_duplicates(subset=["State"])

    for _, row in labeled_no.iterrows():
        cx = row.geometry.centroid.x
        cy = row.geometry.centroid.y
        nm  = short.get(row["State"], row["State"])
        ax.text(cx, cy, nm, fontsize=5.5, ha="center", va="center",
                color="#b0bec5", style="italic")

    ax.set_xlabel("Longitude (degrees East)", fontsize=12, color="#4db6ac", labelpad=10)
    ax.set_ylabel("Latitude (degrees North)",  fontsize=12, color="#4db6ac", labelpad=10)
    ax.tick_params(labelsize=10, colors="#26a69a")
    for spine in ax.spines.values():
        spine.set_edgecolor("#4db6ac")

    ax.set_title(
        "GATEWAYS 2025 — Participant Distribution Across India",
        fontsize=15, fontweight="bold", color="#4db6ac", pad=16
    )

    grey_patch = mpatches.Patch(color="#cfd8dc", label="No participants")
    ax.legend(handles=[grey_patch], loc="lower left", fontsize=9,
              framealpha=0.85, edgecolor="#bbb", labelcolor="#26a69a")

    plt.tight_layout()
    st.pyplot(fig_map)

    # Bubble chart
    st.markdown('<div class="section-header">State-wise Count with Average Rating</div>', unsafe_allow_html=True)
    st_agg = df.groupby("State").agg(
        Participants=("Student Name","count"),
        Avg_Rating  =("Rating","mean")
    ).reset_index()
    st_agg["Avg_Rating"] = st_agg["Avg_Rating"].round(2)
    fig_b = px.scatter(
        st_agg, x="State", y="Participants",
        size="Participants", color="Avg_Rating",
        color_continuous_scale=SEQ_TEAL,
        text="Participants", height=400, size_max=60,
        labels={"Avg_Rating":"Average Rating","Participants":"Number of Participants","State":"State"}
    )
    fig_b.update_traces(textposition="top center")
    fig_b.update_layout(
        font=dict(family="Inter", size=12),
        xaxis=dict(title="State", tickangle=-30, tickfont=dict(size=11)),
        yaxis=dict(title="Number of Participants", tickfont=dict(size=11)),
        coloraxis_colorbar=dict(title="Avg Rating"),
        margin=dict(l=10,r=10,t=20,b=10)
    )
    st.plotly_chart(fig_b, use_container_width=True)

    # Summary table
    st.markdown('<div class="section-header">State Summary Table</div>', unsafe_allow_html=True)
    tbl = df.groupby("State").agg(
        Participants  =("Student Name","count"),
        Colleges      =("College","nunique"),
        Avg_Rating    =("Rating","mean"),
        Total_Revenue =("Amount Paid","sum"),
    ).reset_index()
    tbl["Avg_Rating"]    = tbl["Avg_Rating"].round(2)
    tbl["Total_Revenue"] = tbl["Total_Revenue"].apply(lambda x: f"Rs. {x:,}")
    tbl.columns = ["State","Participants","Colleges","Average Rating","Total Revenue"]
    st.dataframe(
        tbl.sort_values("Participants", ascending=False).reset_index(drop=True),
        use_container_width=True
    )
