import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Global Inventory & Sales")

BASE_URL = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
INV_GID = "0" 

# ACTION: Ensure these GIDs match your specific country tabs
SALES_GIDS = {
    "🇺🇸 US": "111", 
    "🇨🇦 CA": "222",
    "🇬🇧 UK": "333",
    "🇦🇺 AU": "444",
    "🇪🇺 EU": "555"
}

CAMERAS = ["MA-HK", "MA-KRM", "MA-CMR", "MA-MN", "MA-MK", "MC-MIKAYO", "MC-AKITO", "MK-MEOWIE", "MK-ZIPPY", "MK-SP", "MP-KOKO", "MP-HK", "MP-KRM", "MP-CMR", "MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP", "MV-IRIS"]
ACCESSORIES = ["mp2-pp-40", "MP2-PP-120", "MICROSD-32", "MP-PAPER", "TML-TML-SPROUT", "BAG-UNICORN", "BAG-KMTGREEN", "BAG-LITTLEBEE", "BAG-HK", "BAG-KRM", "BAG-CMR", "LANYARD-GREEN", "LANYARD-PINK", "LANYARD-RED", "LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load_data(gid):
    url = f"{BASE_URL}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

st.sidebar.title("📊 Control Panel")
page = st.sidebar.radio("Navigate to:", ["📦 Inventory Overview", "💰 Sales Performance"])

if page == "📦 Inventory Overview":
    st.title("Inventory SKU Breakdown")
    df_inv = load_data(INV_GID)
    market = st.radio("Select Market:", ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"], horizontal=True)
    market_map = {"🇺🇸 US": 7, "🇨🇦 CA": 15, "🇬🇧 UK": 22, "🇦🇺 AU": 29, "🇪🇺 EU": 38}
    selected_col = market_map[market]

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

elif page == "💰 Sales Performance":
    st.title("Daily Sales Analysis")
    region = st.selectbox("Select Region:", list(SALES_GIDS.keys()))
    period = st.selectbox("Compare Recent Day vs:", ["Last Week", "Last Month"])

    try:
        df_sales = load_data(SALES_GIDS[region])
        
        # This makes the column names lowercase so we don't have capitalization errors
        df_sales.columns = [c.strip().lower() for c in df_sales.columns]
        
        # Correctly identifying columns even with capitalization
        df_sales['date'] = pd.to_datetime(df_sales['date']).dt.date
        
        recent_date = df_sales['date'].max()
        if period == "Last Week": compare_date = recent_date - timedelta(days=7)
        else: compare_date = recent_date - timedelta(days=30)

        recent_day = df_sales[df_sales['date'] == recent_date]
        compare_day = df_sales[df_sales['date'] == compare_date]

        st.write(f"### Results: {recent_date} vs {compare_date}")
        
        # Calculation
        r_total = pd.to_numeric(recent_day['quantity'], errors='coerce').sum()
        c_total = pd.to_numeric(compare_day['quantity'], errors='coerce').sum()
        
        st.metric("Units Sold Today", f"{int(r_total)}", delta=int(r_total - c_total))

        # SKU Comparison Table
        r_sku = recent_day.groupby('sku')['quantity'].sum().reset_index()
        c_sku = compare_day.groupby('sku')['quantity'].sum().reset_index()
        
        comparison = pd.merge(r_sku, c_sku, on='sku', how='outer', suffixes=('_Recent', '_Prev')).fillna(0)
        comparison['Change'] = comparison['quantity_Recent'] - comparison['quantity_Prev']
        
        st.write("### SKU Performance Detail")
        # Rename columns back to nice names for display
        comparison.columns = ["SKU Name", "Recent Qty", "Previous Qty", "Change"]
        st.dataframe(comparison.sort_values('Recent Qty', ascending=False), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error reading Sales data: {e}")
        st.info("Ensure your Sales tab has 'Date', 'SKU', and 'Quantity' columns.")
