import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(layout="wide", page_title="Global Inventory Dashboard")

# The exact URL of your Google Sheet
# Make sure this is the link you get from the "Share" button
url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/edit?usp=sharing"

# Create a connection object
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # We tell Streamlit the sheet URL and exactly which worksheet to read
    # If the tab name is exactly 'Shopify', it will find it!
    tab_name = "Shopify".strip()
    df = conn.read(spreadsheet=url, worksheet=tab_name, ttl="5m")

    st.markdown("<h2 style='text-align: center;'>📦 Global Stock Levels</h2>", unsafe_allow_html=True)
    st.write("---")

    # Creating 5 columns
    m1, m2, m3, m4, m5 = st.columns(5)

    # Calculation logic for columns H, P, W, AD, AM
    with m1:
        us_val = pd.to_numeric(df.iloc[:, 7], errors='coerce').sum()
        st.metric("🇺🇸 US Shopify", f"{int(us_val):,}")
    with m2:
        ca_val = pd.to_numeric(df.iloc[:, 15], errors='coerce').sum()
        st.metric("🇨🇦 CA Shopify", f"{int(ca_val):,}")
    with m3:
        uk_val = pd.to_numeric(df.iloc[:, 22], errors='coerce').sum()
        st.metric("🇬🇧 UK Shopify", f"{int(uk_val):,}")
    with m4:
        au_val = pd.to_numeric(df.iloc[:, 29], errors='coerce').sum()
        st.metric("🇦🇺 AU Shopify", f"{int(au_val):,}")
    with m5:
        eu_val = pd.to_numeric(df.iloc[:, 38], errors='coerce').sum()
        st.metric("🇪🇺 EU Shopify", f"{int(eu_val):,}")

    st.success("Connected to Google Sheets successfully!")

except Exception as e:
    st.error("Connection Issue")
    st.write("Streamlit is having trouble reading that specific tab.")
    st.info("Check: Is the tab name exactly 'Shopify' (no extra spaces)?")
    st.write(f"Error details: {e}")
