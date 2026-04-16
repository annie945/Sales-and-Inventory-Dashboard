import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup
st.set_page_config(layout="wide", page_title="Global Inventory & Sales")

BASE = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"
GIDS = {
    "🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"
}
CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
ACCS = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT","BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM","BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid): return pd.read_csv(f"{BASE}&gid={gid}")

def is_cam(s): return any(x in str(s).upper() for x in CAMS)
def is_acc(s): return any(x in str(s).upper() for x in ACCS)

page = st.sidebar.radio("Navigation", ["📦 Inventory", "💰 Sales"])

# --- INVENTORY ---
if page == "📦 Inventory":
    st.title("📦 Inventory Stock")
    try:
        df = load("0")
        m_label = st.radio("Market:", list(GIDS.keys()), horizontal=True)
        m_idx = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}[m_label]
        sku_df = df.iloc[:, [0, m_idx]].copy()
        sku_df.columns = ["SKU", "Stock"]
        sku_df = sku_df.dropna(subset=["SKU"])
        sku_df["Stock"] = pd.to_numeric(sku_df["Stock"], errors='coerce').fillna(0).astype(int)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            sub_c = sku_df[sku_df["SKU"].apply(is_cam)]
            st.metric("Total Cameras", f"{sub_c['Stock'].sum():,}")
            st.dataframe(sub_c, use_container_width=True, hide_index=True)
        with c2:
            st.subheader("🎒 Accessories")
            sub_a = sku_df[sku_df["SKU"].apply(is_acc)]
            st.metric("Total Accessories", f"{sub_a['Stock'].sum():,}")
            st.dataframe(sub_a, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Inventory Error: {e}")

# --- SALES ---
elif page == "💰 Sales":
    st.title("💰 Weekly & YTD Performance")
    reg = st.sidebar.selectbox("Region", list(GIDS.keys()))
    try:
        df = load(GIDS[reg])
        df.columns = [str(c).strip().lower() for c in df.columns]
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df[~df['sku'].str.contains('unknown|worry-free|delivery', case=False, na=False)]

        latest = df['date'].max()
        start = latest - timedelta(days=6)
        p_start, p_end = start - timedelta(days=7), start - timedelta(days=1)

        curr = df[(df['date'] >= start) & (df['date'] <= latest)].copy()
        prev = df[(df['date'] >= p_start) & (df['date'] <= p_end)].copy()
        ytd = df[pd.to_datetime(df['date']).dt.year == latest.year].copy()
        ytd_sum = ytd.groupby('sku')['quantity'].sum().reset_index()

        st.write(f"**Weekly View:** {start} to {latest} (vs {p_start} to {p_end})")
        c1, col2 = st.columns(2)
        with c1:
            v = curr[curr['sku'].apply(is_cam)]['quantity'].sum()
            o = prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Weekly Camera", int(v), delta=int(v-o))
        with col2:
            v = curr[curr['sku'].apply(is_acc)]['quantity'].sum()
            o = prev[prev['sku'].apply(is_acc)]['quantity'].sum()
            st.metric("🎒 Weekly Accessory", int(
