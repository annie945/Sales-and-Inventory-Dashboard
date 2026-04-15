import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuration
st.set_page_config(layout="wide", page_title="Global Inventory & Sales")

BASE_URL = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
INV_GID = "0"  # Your Shopify Inventory tab

# ACTION: Fill in your actual GIDs for the Sales tabs
SALES_GIDS = {
    "🇺🇸 US": "1304392959", 
    "🇨🇦 CA": "634720426",
    "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385",
    "🇪🇺 EU": "975667344"
}

# SKU Lists for Inventory Grouping
CAMERAS = ["MA-HK", "MA-KRM", "MA-CMR", "MA-MN", "MA-MK", "MC-MIKAYO", "MC-AKITO", "MK-MEOWIE", "MK-ZIPPY", "MK-SP", "MP-KOKO", "MP-HK", "MP-KRM", "MP-CMR", "MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP", "MV-IRIS"]
ACCESSORIES = ["mp2-pp-40", "MP2-PP-120", "MICROSD-32", "MP-PAPER", "TML-TML-SPROUT", "BAG-UNICORN", "BAG-KMTGREEN", "BAG-LITTLEBEE", "BAG-HK", "BAG-KRM", "BAG-CMR", "LANYARD-GREEN", "LANYARD-PINK", "LANYARD-RED", "LANYARD-PURPLE"]

# 2. Data Loading Functions
@st.cache_data(ttl=300)
def load_data(gid):
    url = f"{BASE_URL}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("📊 Control Panel")
page = st.sidebar.radio("Navigate to:", ["📦 Inventory Overview", "💰 Sales Performance"])

# --- PAGE 1: INVENTORY ---
if page == "📦 Inventory Overview":
    st.title("Inventory SKU Breakdown")
    df_inv = load_data(INV_GID)
    
    market = st.radio("Select Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
    market_map = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
    selected_col = market_map[market]

    # Process Inventory Data
    sku_stock = df_inv.iloc[:, [0, selected_col]].copy()
    sku_stock.columns = ["SKU Name", "Stock"]
    sku_stock = sku_stock.dropna(subset=["SKU Name"])
    sku_stock["Stock"] = pd.to_numeric(sku_stock["Stock"], errors='coerce').fillna(0).astype(int)

    def categorize(sku):
        s = str(sku).upper().strip()
        if any(cam.upper() in s for cam in CAMERAS): return "📸 Camera"
        if any(acc.upper() in s for acc in ACCESSORIES): return "🎒 Accessory"
        return "Other"
    
    sku_stock["Category"] = sku_stock["SKU Name"].apply(categorize)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📸 Cameras")
        cam_df = sku_stock[sku_stock["Category"] == "📸 Camera"]
        st.metric(f"{market} Camera Total", f"{cam_df['Stock'].sum():,}")
        st.dataframe(cam_df[["SKU Name", "Stock"]], use_container_width=True, hide_index=True)
    with c2:
        st.subheader("🎒 Accessories")
        acc_df = sku_stock[sku_stock["Category"] == "🎒 Accessory"]
        st.metric(f"{market} Accessory Total", f"{acc_df['Stock'].sum():,}")
        st.dataframe(acc_df[["SKU Name", "Stock"]], use_container_width=True, hide_index=True)

# --- PAGE 2: SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title("Daily Sales Analysis")
    region = st.selectbox("Select Region:", list(SALES_GIDS.keys()))
    period = st.selectbox("Compare Recent Day vs:", ["Last Week", "Last Month", "Custom Date"])

    try:
        df_sales = load_data(SALES_GIDS[region])
        # Ensure your Sales tab has columns: 'Date', 'SKU', and 'Quantity'
        df_sales['Date'] = pd.to_datetime(df_sales['Date']).dt.date
        
        recent_date = df_sales['Date'].max()
        if period == "Last Week": compare_date = recent_date - timedelta(days=7)
        elif period == "Last Month": compare_date = recent_date - timedelta(days=30)
        else: compare_date = st.date_input("Select date:", recent_date - timedelta(days=1))

        recent_day = df_sales[df_sales['Date'] == recent_date]
        compare_day = df_sales[df_sales['Date'] == compare_date]

        # Summary Metrics
        st.write(f"### Results: {recent_date} vs {compare_date}")
        r_total = recent_day['Quantity'].sum()
        c_total = compare_day['Quantity'].sum()
        
        st.metric("Units Sold", f"{int(r_total)}", delta=int(r_total - c_total))

        # Comparison Table
        r_sku = recent_day.groupby('SKU')['Quantity'].sum().reset_index()
        c_sku = compare_day.groupby('SKU')['Quantity'].sum().reset_index()
        comparison = pd.merge(r_sku, c_sku, on='SKU', how='outer', suffixes=('_Recent', '_Prev')).fillna(0)
        comparison['Change'] = comparison['Quantity_Recent'] - comparison['Quantity_Prev']
        
        st.write("### SKU Performance Change")
        st.dataframe(comparison.sort_values('Quantity_Recent', ascending=False), use_container_width=True)

    except Exception as e:
        st.error("Check your Sales Tab columns: They must be named 'Date', 'SKU', and 'Quantity'.")
