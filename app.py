import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Market Stock Breakdown")

# 1. Base URL & Tab ID
base_url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
gid_number = "0" 
direct_url = f"{base_url}/export?format=csv&gid={gid_number}"

# 2. SKU Group Lists
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
    
    # Market Selector
    market = st.radio("Select Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
    market_map = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
    selected_col = market_map[market]

    # Prepare Data
    sku_stock = df.iloc[:, [0, selected_col]].copy()
    sku_stock.columns = ["SKU Name", "Stock"]
    sku_stock = sku_stock.dropna(subset=["SKU Name"])
    sku_stock["Stock"] = pd.to_numeric(sku_stock["Stock"], errors='coerce').fillna(0).astype(int)

    # Function to Categorize
    def categorize(sku):
        sku_upper = str(sku).upper().strip()
        if any(cam in sku_upper for cam in [c.upper() for c in CAMERAS]):
            return "📸 Camera"
        if any(acc in sku_upper for acc in [a.upper() for a in ACCESSORIES]):
            return "🎒 Accessory"
        return "Other"

    sku_stock["Category"] = sku_stock["SKU Name"].apply(categorize)

    # --- DISPLAY SECTIONS ---
    
    # Section 1: Cameras
    st.subheader("📸 Cameras")
    cam_df = sku_stock[sku_stock["Category"] == "📸 Camera"]
    if not cam_df.empty:
        # Show total for this group
        st.metric("Total Camera Units", f"{cam_df['Stock'].sum():,}")
        st.dataframe(
