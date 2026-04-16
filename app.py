import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup
st.set_page_config(layout="wide", page_title="Global Inventory & Sales")

BASE = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"
SALES_GIDS = {
    "🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"
}
CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
ACCS = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT","BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM","BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid): return pd.read_csv(f"{BASE}&gid={gid}")

page = st.sidebar.radio("Menu", ["📦 Inventory", "💰 Sales"])

# --- INVENTORY PAGE ---
if page == "📦 Inventory":
    st.title("Inventory Stock")
    try:
        df = load("0")
        m_label = st.radio("Market", list(SALES_GIDS.keys()), horizontal=True)
        m_idx = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}[m_label]
        sku_df = df.iloc[:, [0, m_idx]].copy()
        sku_df.columns = ["SKU", "Stock"]
        sku_df["Stock"] = pd.to_numeric(sku_df["Stock"], errors='coerce').fillna(0).astype(int)

        def get_cat(sku):
            s = str(sku).upper().strip()
            if any(x in s for x in CAMS): return "📸 Camera"
            if any(x in s for x in ACCS): return "🎒 Accessory"
            return "Other"
        
        sku_df["Cat"] = sku_df["SKU"].apply(get_cat)
        c1, c2 = st.columns(2)
        for cat, col in [("📸 Camera", c1), ("🎒 Accessory", c2)]:
            with col:
                sub = sku_df[sku_df["Cat"] == cat]
                st.metric(f"Total {cat}", f"{sub['Stock'].sum():,}")
                st.dataframe(sub[["SKU", "Stock"]], use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Error: {e}")

# --- SALES PAGE ---
elif page == "💰 Sales":
    st.title("Sales Analysis")
    reg = st.selectbox("Region", list(SALES_GIDS.keys()))
    d1, d2 = st.columns(2)
    with d1: start = st.date_input("From", datetime.now() - timedelta(7))
    with d2: end = st.date_input("To", datetime.now())

    try:
        df = load(SALES_GIDS[reg])
        df.columns = [str(c).strip().lower() for c in df_sales_cols := df.columns]
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df[~df['sku'].str.contains('unknown|worry-free', case=False, na=False)]
        
        diff = (end - start).days + 1
        curr = df[(df['date'] >= start) & (df['date'] <= end)]
        prev = df[(df['date'] >= (start - timedelta(diff))) & (df['date'] <= (end - timedelta(diff)))]

        r_tot, p_tot = curr['quantity'].sum(), prev['quantity'].sum()
        st.metric(f"Total Units ({diff} Days)", f"{int(r_tot)}", delta=int(r_tot - p_tot))

        # 1. Model Type Breakdown (Cameras Only)
        st.subheader("📸 Model Line Comparison (Cameras Only)")
        def get_model(sku):
            s = str(sku).upper()
            if not any(c in s for c in CAMS): return None
            if s.startswith("MA-"): return "Model A"
            if s.startswith("MC-"): return "Model C"
            if s.startswith("MK-"): return "Model K"
            if s.startswith("MP2-"): return "Model P2"
            if s.startswith("MP-"): return "Model P"
            return None

        curr['Model'] = curr['sku'].apply(get_model)
        prev['Model'] = prev['sku'].apply(get_model)
        
        m_curr = curr.groupby('Model')['quantity'].sum()
        m_prev = prev.groupby('Model')['quantity'].sum()
        m_comp = pd.concat([m_curr, m_prev], axis=1, keys=['Current', 'Previous']).fillna(0)
        st.table(m_comp.style.format("{:.0f}"))

        # 2. Comparison
