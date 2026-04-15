import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Global Inventory & Sales Dashboard")

# 2. Base Configuration
BASE_URL = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
INV_GID = "0" 

# Your specific Sales Tab GIDs
SALES_GIDS = {
    "🇺🇸 US": "1304392959", 
    "🇨🇦 CA": "634720426",
    "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385",
    "🇪🇺 EU": "975667344"
}

# SKU Category Lists
CAMERAS = [
    "MA-HK", "MA-KRM", "MA-CMR", "MA-MN", "MA-MK", "MC-MIKAYO", "MC-AKITO", 
    "MK-MEOWIE", "MK-ZIPPY", "MK-SP", "MP-KOKO", "MP-HK", "MP-KRM", "MP-CMR", 
    "MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP", "MV-IRIS", "MV-IRI"
]

ACCESSORIES = [
    "MP2-PP-40", "MP2-PP-120", "MICROSD-32", "MP-PAPER", "TML-TML-SPROUT", 
    "BAG-UNICORN", "BAG-KMTGREEN", "BAG-LITTLEBEE", "BAG-HK", "BAG-KRM", 
    "BAG-CMR", "LANYARD-GREEN", "LANYARD-PINK", "LANYARD-RED", "LANYARD-PURPLE"
]

# 3. Data Loading Helper
@st.cache_data(ttl=300)
def load_data(gid):
    url = f"{BASE_URL}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

# --- SIDEBAR ---
st.sidebar.title("📊 Control Panel")
page = st.sidebar.radio("Navigate to:", ["📦 Inventory Overview", "💰 Sales Performance"])

# --- PAGE 1: INVENTORY ---
if page == "📦 Inventory Overview":
    st.title("Inventory SKU Breakdown")
    try:
        df_inv = load_data(INV_GID)
        market = st.radio("Select Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
        market_map = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
        selected_col = market_map[market]

        sku_stock = df_inv.iloc[:, [0, selected_col]].copy()
        sku_stock.columns = ["SKU Name", "Stock"]
        sku_stock = sku_stock.dropna(subset=["SKU Name"])
        sku_stock["Stock"] = pd.to_numeric(sku_stock["Stock"], errors='coerce').fillna(0).astype(int)

        # Bulletproof Categorization
        def categorize(sku):
