import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Global Inventory Dashboard")

# 1. YOUR BASE LINK (Everything before /edit)
# Make sure this ID matches yours: 1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs
base_url = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"

# 2. YOUR TAB ID (GID) 
# Replace the number below with the GID you copied in Step 1
gid_number = "0" 

# 3. Create the direct download link
direct_url = f"{base_url}/export?format=csv&gid={gid_number}"

@st.cache_data(ttl=300)
def load_data():
    # We use error_bad_lines=False just in case your sheet has messy formatting
    return pd.read_csv(direct_url)

try:
    df = load_data()

    st.markdown("<h2 style='text-align: center;'>📦 Global Stock Levels</h2>", unsafe_allow_html=True)
    st.write("---")

    m1, m2, m3, m4, m5 = st.columns(5)

    # Columns H(7), P(15), W(22), AD(29), AM(38)
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

    st.success("System Live & Connected!")

except Exception as e:
    st.error("Connection Failed")
    st.write("Check if your Google Sheet is set to 'Anyone with the link can view'.")
    st.write(f"Error details: {e}")
