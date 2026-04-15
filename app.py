import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Global Inventory")

# 1. Your Base URL (Everything between /d/ and /edit)
base_url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"

# 2. Your Specific Tab ID (GID)
# Double check your browser address bar: if the number after gid= is different, change it here!
tab_id = "1116131481" 

# 3. Build the export link correctly
csv_url = f"{base_url}/export?format=csv&gid={tab_id}"

@st.cache_data(ttl=600)
def load_data():
    # We use 'header=0' to ensure it reads the top row correctly
    data = pd.read_csv(csv_url)
    return data

try:
    df = load_data()

    # Dashboard Styling
    st.markdown("<h2 style='text-align: center; color: #333;'>📦 Inventory Stock Levels</h2>", unsafe_allow_html=True)
    st.write("---")

    # Creating the 5 Market Columns
    m1, m2, m3, m4, m5 = st.columns(5)

    # We convert values to numbers and sum them, ignoring errors (like text or empty cells)
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

    st.success("Connection Successful!")

except Exception as e:
    st.error("Connection Refused")
    st.write("Please check your GID. Open the sheet tab 'WOS Summary-Shopify' and look at the end of the URL for the gid= number.")
    st.write(f"Error details: {e}")
