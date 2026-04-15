import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup
st.set_page_config(layout="wide", page_title="Global Inventory & Sales")

BASE_URL = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
INV_GID = "0" 
SALES_GIDS = {
    "🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"
}

CAMERAS = ["MA-HK", "MA-KRM", "MA-CMR", "MA-MN", "MA-MK", "MC-MIKAYO", "MC-AKITO", "MK-MEOWIE", "MK-ZIPPY", "MK-SP", "MP-KOKO", "MP-HK", "MP-KRM", "MP-CMR", "MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP", "MV-IRIS", "MV-IRI"]
ACCESSORIES = ["MP2-PP-40", "MP2-PP-120", "MICROSD-32", "MP-PAPER", "TML-TML-SPROUT", "BAG-UNICORN", "BAG-KMTGREEN", "BAG-LITTLEBEE", "BAG-HK", "BAG-KRM", "BAG-CMR", "LANYARD-GREEN", "LANYARD-PINK", "LANYARD-RED", "LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load_data(gid):
    return pd.read_csv(f"{BASE_URL}/export?format=csv&gid={gid}")

# --- Navigation ---
page = st.sidebar.radio("Navigate to:", ["📦 Inventory", "💰 Sales"])

# --- Page 1: Inventory ---
if page == "📦 Inventory":
    st.title("Inventory Stock")
    try:
        df = load_data(INV_GID)
        m_label = st.radio("Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
        m_cols = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
        
        sku_df = df.iloc[:, [0, m_cols[m_label]]].copy()
        sku_df.columns = ["SKU", "Stock"]
        sku_df["Stock"] = pd.to_numeric(sku_df["Stock"], errors='coerce').fillna(0).astype(int)

        def get_cat(sku):
            s = str(sku).upper().strip()
            if any(c in s for c in CAMERAS): return "📸 Camera"
            if any(a in s for a in ACCESSORIES): return "🎒 Accessory"
            return "Other"
        
        sku_df["Cat"] = sku_df["SKU"].apply(get_cat)
        c1, c2 = st.columns(2)
        for cat, col in [("📸 Camera", c1), ("🎒 Accessory", c2)]:
            with col:
                sub = sku_df[sku_df["Cat"] == cat]
                st.metric(f"Total {cat}", f"{sub['Stock'].sum():,}")
                st.dataframe(sub[["SKU", "Stock"]], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error: {e}")

# --- Page 2: Sales ---
elif page == "💰 Sales":
    st.title("Sales Analysis")
    reg = st.selectbox("Region:", list(SALES_GIDS.keys()))
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", datetime.now() - timedelta(7))
    with c2: end = st.date_input("To", datetime.now())

    try:
        df = load_data(SALES_GIDS[reg])
        df.columns = [str(c).strip().lower() for c in df.columns]
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Filters
        df = df[~df['sku'].str.contains('unknown|worry-free', case=False, na=False)]
        
        curr = df[(df['date'] >= start) & (df['date'] <= end)]
        diff = (end - start).days + 1
        prev = df[(df['date'] >= (start - timedelta(diff))) & (df['date'] <= (end - timedelta(diff)))]

        r_tot, p_tot = curr['quantity'].sum(), prev['quantity'].sum()
        st.metric(f"Units Sold ({diff} days)", f"{int(r_tot)}", delta=int(r_tot - p_tot))

        r_sku = curr.groupby('sku')['quantity'].sum().reset_index()
        p_sku = prev.groupby('sku')['quantity'].sum().reset_index()
        comp = pd.merge(r_sku, p_sku, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        comp['Change'] = comp['quantity_c'] - comp['quantity_p']
        
        st.write("### SKU Details")
        comp.columns = ["SKU", "Current", "Previous", "Change"]
        st.dataframe(comp.sort_values('Current', ascending=False), use_container_width=True, hide_index=True)
    except Exception as
