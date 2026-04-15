import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Global Inventory")

# Your exact Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/edit?usp=sharing"

# This part is crucial: we are telling it the exact GID (Tab ID) for 'WOS Summary-Shopify'
# Based on your previous description, I've added the logic to target the tab properly
csv_url = SHEET_URL.replace('/edit?usp=sharing', '/export?format=csv&gid=1116131481')

@st.cache_data(ttl=600)
def load_data():
    # skipfooter helps if there are random notes at the bottom of the sheet
    data = pd.read_csv(csv_url)
    return data

try:
    df = load_data()

    st.markdown("<h2 style='text-align: center;'>📦 Inventory Stock Levels</h2>", unsafe_allow_html=True)
    st.write("---")

    # Creating the 5 Market Columns
    m1, m2, m3, m4, m5 = st.columns(5)

    # Note: Column H is index 7, P is 15, W is 22, AD is 29, AM is 38
    with m1:
        val = pd.to_numeric(df.iloc[:, 7], errors='coerce').sum()
        st.metric("🇺🇸 US Shopify", f"{int(val):,}")
    with m2:
        val = pd.to_numeric(df.iloc[:, 15], errors='coerce').sum()
        st.metric("🇨🇦 CA Shopify", f"{int(val):,}")
    with m3:
        val = pd.to_numeric(df.iloc[:, 22], errors='coerce').sum()
        st.metric("🇬🇧 UK Shopify", f"{int(val):,}")
    with m4:
        val = pd.to_numeric(df.iloc[:, 29], errors='coerce').sum()
        st.metric("🇦🇺 AU Shopify", f"{int(val):,}")
    with m5:
        val = pd.to_numeric(df.iloc[:, 38], errors='coerce').sum()
        st.metric("🇪🇺 EU Shopify", f"{int(val):,}")

except Exception as e:
    st.error("Sheet Loading Error")
    st.info("Check if the GID (Tab ID) matches. Open your sheet, click the 'WOS Summary-Shopify' tab, and look at the number after 'gid=' in your browser address bar.")
    st.write(e)
