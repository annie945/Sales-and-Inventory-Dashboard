import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="SKU Stock Breakdown")

# 1. Configuration
base_url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
gid_number = "0" 
direct_url = f"{base_url}/export?format=csv&gid={gid_number}"

# 2. Group Definitions
CAMERAS = [
    "MA-HK", "MA-KRM", "MA-CMR", "MA-MN", "MA-MK", "MC-MIKAYO", "MC-AKITO", 
    "MK-MEOWIE", "MK-ZIPPY", "MK-SP", "MP-KOKO", "MP-HK", "MP-KRM", "MP-CMR", 
    "MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP", "MV-IRIS"
]

ACCESSORIES = [
    "mp2-pp-40", "MP2-PP-120", "MICROSD-32", "MP-PAPER", "TML-TML-SPROUT", 
    "BAG-UNICORN", "BAG-KMTGREEN", "BAG-LITTLEBEE", "BAG-HK", "BAG-KRM", 
    "BAG-CMR", "LANYARD-GREEN", "LANYARD-PINK", "LANYARD-RED", "LANYARD-PURPLE"
]

@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(direct_url)

try:
    df = load_data()

    st.title("📦 SKU Stock by Category")
    
    # Market Selector Pills
    market = st.radio("Select Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
    market_map = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
    selected_col = market_map[market]

    # Process Data
    sku_stock = df.iloc[:, [0, selected_col]].copy()
    sku_stock.columns = ["SKU Name", "Stock"]
    sku_stock = sku_stock.dropna(subset=["SKU Name"])
    sku_stock["Stock"] = pd.to_numeric(sku_stock["Stock"], errors='coerce').fillna(0).astype(int)

    # Categorization Logic
    def categorize(sku):
        s = str(sku).upper().strip()
        if any(cam.upper() in s for cam in CAMERAS): return "📸 Camera"
        if any(acc.upper() in s for acc in ACCESSORIES): return "🎒 Accessory"
        return "Other"

    sku_stock["Category"] = sku_stock["SKU Name"].apply(categorize)

    # --- DISPLAY ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📸 Cameras")
        cam_df = sku_stock[sku_stock["Category"] == "📸 Camera"]
        st.metric("Total Camera Stock", f"{cam_df['Stock'].sum():,}")
        st.dataframe(cam_df[["SKU Name", "Stock"]], use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🎒 Accessories")
        acc_df = sku_stock[sku_stock["Category"] == "🎒 Accessory"]
        st.metric("Total Accessory Stock", f"{acc_df['Stock'].sum():,}")
        st.dataframe(acc_df[["SKU Name", "Stock"]], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
