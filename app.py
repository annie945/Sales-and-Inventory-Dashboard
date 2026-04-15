import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="SKU Stock Dashboard")

# 1. Base URL & Tab ID (Shopify Tab)
base_url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
gid_number = "0" 
direct_url = f"{base_url}/export?format=csv&gid={gid_number}"

@st.cache_data(ttl=300)
def load_data():
    # We load the data and skip the first few empty/header rows if necessary
    # Based on your sheet, Column A (index 0) is usually the SKU name
    return pd.read_csv(direct_url)

try:
    df = load_data()

    st.title("📦 SKU Stock Breakdown")
    st.write("---")

    # 2. Market Selection Pills (Like your original image!)
    market = st.radio(
        "Select Market to view SKU Details:",
        ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU", "🇪🇺 EU"],
        horizontal=True
    )

    # Map the selection to your specific columns
    # Column A=0(SKU), H=7(US), P=15(CA), W=22(UK), AD=29(AU), AM=38(EU)
    market_map = {
        "🇺🇸 US": 7,
        "🇨🇦 CA": 15,
        "🇬🇧 UK": 22,
        "🇦🇺 AU": 29,
        "🇪🇺 EU": 38
    }
    
    selected_col = market_map[market]

    # 3. Create a clean Dataframe for the selected market
    # We take Column 0 (SKU Name) and the selected Market Column
    sku_stock = df.iloc[:, [0, selected_col]].copy()
    sku_stock.columns = ["SKU Name", "Current Stock"]
    
    # Clean up: Remove empty rows or rows where SKU is missing
    sku_stock = sku_stock.dropna(subset=["SKU Name"])
    sku_stock["Current Stock"] = pd.to_numeric(sku_stock["Current Stock"], errors='coerce').fillna(0).astype(int)

    # 4. Display the Data
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(f"Total {market} Stock")
        st.header(f"{sku_stock['Current Stock'].sum():,}")
        st.info("Top 5 SKUs by Stock Level")
        st.table(sku_stock.nlargest(5, "Current Stock"))

    with col2:
        st.subheader("Full SKU List")
        # Search box to find a specific SKU quickly
        search = st.text_input("🔍 Search SKU Name:")
        if search:
            sku_stock = sku_stock[sku_stock["SKU Name"].str.contains(search, case=False)]
        
        st.dataframe(sku_stock, use_container_width=True, height=500)

except Exception as e:
    st.error("Data Load Error")
    st.write(e)
