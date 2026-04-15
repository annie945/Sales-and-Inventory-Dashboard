import streamlit as st
import pandas as pd

# Setting page to wide mode to look like a professional dashboard
st.set_page_config(layout="wide")

# The URL of your Google Sheet (Make sure it's "Anyone with link can view")
SHEET_URL = "YOUR_GOOGLE_SHEET_URL_HERE"
# We convert the URL to export as CSV so Streamlit can read it easily
csv_url = SHEET_URL.replace('/edit#gid=', '/export?format=csv&gid=')

# Load the data
@st.cache_data(ttl=600) # Refreshes every 10 minutes
def load_data():
    # We read the 'WOS Summary-Shopify' tab specifically
    df = pd.read_csv(csv_url) 
    return df

try:
    df = load_data()

    # --- DASHBOARD HEADER ---
    st.markdown("<h1 style='text-align: center; color: #1E1E1E;'>Global Inventory Overview</h1>", unsafe_allow_html=True)
    
    # --- CALCULATE TOTALS FROM YOUR COLUMNS ---
    # Note: We use .iloc or header names. Adjusting based on your column letters:
    us_stock = df.iloc[:, 7].sum()   # Column H (Index 7)
    ca_stock = df.iloc[:, 15].sum()  # Column P (Index 15)
    uk_stock = df.iloc[:, 22].sum()  # Column W (Index 22)
    au_stock = df.iloc[:, 29].sum()  # Column AD (Index 29)
    eu_stock = df.iloc[:, 38].sum()  # Column AM (Index 38)

    # --- TOP ROW: KPI CARDS (Matching your image) ---
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(label="🇺🇸 US Shopify", value=f"{int(us_stock):,}")
    with col2:
        st.metric(label="🇨🇦 CA Shopify", value=f"{int(ca_stock):,}")
    with col3:
        st.metric(label="🇬🇧 UK Shopify", value=f"{int(uk_stock):,}")
    with col4:
        st.metric(label="🇦🇺 AU Shopify", value=f"{int(au_stock):,}")
    with col5:
        st.metric(label="🇪🇺 EU Shopify", value=f"{int(eu_stock):,}")

    st.divider()

    # --- NEXT STEP: ADDING SALES ---
    st.info("Inventory loaded successfully. Ready to add 'Daily Sales' data to the next section.")

except Exception as e:
    st.error("Connection Error: Make sure your Google Sheet is set to 'Anyone with link can view'.")
    st.write(e)
