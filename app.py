import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Sales Pro")

# Professional CSS for cleaner tables and metrics
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

BASE = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"
SALES_GIDS = {
    "🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"
}
CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
ACCS = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT","BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM","BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid): return pd.read_csv(f"{BASE}&gid={gid}")

page = st.sidebar.radio("Navigation", ["📦 Inventory Overview", "💰 Sales Performance"])

# Helper for Logic
def is_cam(sku): return any(x in str(sku).upper() for x in CAMS)
def is_acc(sku): return any(x in str(sku).upper() for x in ACCS)
def get_model(sku):
    s = str(sku).upper().strip()
    if not is_cam(s): return None
    if s.startswith("MA-"): return "Model A"
    if s.startswith("MC-"): return "Model C"
    if s.startswith("MK-"): return "Model K"
    if s.startswith("MP2-"): return "Model P2"
    if s.startswith("MP-"): return "Model P"
    return None # Returns None for anything else to hide "Other Camera"

# --- INVENTORY PAGE ---
if page == "📦 Inventory Overview":
    st.title("📦 Inventory Stock")
    try:
        df = load("0")
        m_label = st.radio("Select Market:", list(SALES_GIDS.keys()), horizontal=True)
        m_idx = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}[m_label]
        
        sku_df = df.iloc[:, [0, m_idx]].copy()
        sku_df.columns = ["SKU", "Stock"]
        sku_df = sku_df.dropna(subset=["SKU"])
        sku_df["Stock"] = pd.to_numeric(sku_df["Stock"], errors='coerce').fillna(0).astype(int)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            sub_c = sku_df[sku_df["SKU"].apply(is_cam)]
            st.metric("Total Camera Stock", f"{sub_c['Stock'].sum():,}")
            st.dataframe(sub_c, use_container_width=True, hide_index=True)
        with c2:
            st.subheader("🎒 Accessories")
            sub_a = sku_df[sku_df["SKU"].apply(is_acc)]
            st.metric("Total Accessory Stock", f"{sub_a['Stock'].sum():,}")
            st.dataframe(sub_a, use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Error loading inventory: {e}")

# --- SALES PAGE ---
elif page == "💰 Sales Performance":
    st.title("💰 Sales Performance Analysis")
    reg = st.sidebar.selectbox("Region", list(SALES_GIDS.keys()))

    try:
        df = load(SALES_GIDS[reg])
        df.columns = [str(c).strip().lower() for c in df.columns]
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df[~df['sku'].str.contains('unknown|worry-free|delivery', case=False, na=False)]

        # Dates
        end_date = df['date'].max()
        start_date = end_date - timedelta(days=6)
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)

        curr = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
        prev = df[(df['date'] >= prev_start) & (df['date'] <= prev_end)].copy()

        # 1. Metrics Header
        st.markdown(f"**Comparison Range:** {start_date} to {end_date} (vs {prev_start} to {prev_end})")
        col1, col2 = st.columns(2)
        with col1:
            val = curr[curr['sku'].apply(is_cam)]['quantity'].sum()
            old = prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Camera Units", int(val), delta=int(val - old))
        with col2:
            val = curr[curr['sku'].apply(is_acc)]['quantity'].sum()
            old = prev[prev['sku'].apply(is_acc)]['quantity'].sum()
            st.metric("🎒 Accessory Units", int(val), delta=int(val - old))

        st.divider()

        # 2. Line Chart (Cleaner)
        st.subheader("📈 Monthly Sales Trend per Model")
        df_trend = df.copy()
        df_trend['Model'] = df_trend['sku'].apply(get_model)
        df_trend = df_trend.dropna(subset=['Model']) # Automatically hides "Other Camera"
        df_trend['Month'] = pd.to_datetime(df_trend['date']).dt.strftime('%Y-%m')
        
        trend_pivot = df_trend.groupby(['Month', 'Model'])['quantity'].sum().unstack().fillna(0)
        st.line_chart(trend_pivot, height=400)

        # 3. Tables
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📊 Model Summary")
            curr['Model'] = curr['sku'].apply(get_model)
            prev['Model'] = prev['sku'].apply(get_model)
            m_curr = curr.dropna(subset=['Model']).groupby('Model')['quantity'].sum()
            m_prev = prev.dropna(subset=['Model']).groupby('Model')['quantity'].sum()
            m_comp = pd.concat([m_curr, m_prev], axis=1, keys=['Current', 'Previous']).fillna(0)
            st.dataframe(m_comp.style.format("{:.0f}"), use_container_width=True)

        with c2:
            st.subheader("📦 SKU Detail")
            r_sku = curr.groupby('sku')['quantity'].sum().reset_index()
            p_sku = prev.groupby('sku')['quantity'].sum().reset_index()
            comp = pd.merge(r_sku, p_sku, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
            comp['Change'] = comp['quantity_c'] - comp['quantity_p']
            comp.columns = ["SKU", "Curr Qty", "Prev Qty", "Delta"]
            st.dataframe(comp.sort_values('Curr Qty', ascending=False), use_container_width=True, hide_index=True)

    except Exception as e: st.error(f"Sales Data Error: {e}")
