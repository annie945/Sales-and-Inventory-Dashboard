import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup
st.set_page_config(layout="wide", page_title="Dashboard")

B = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"
G = {"🇺🇸 US":"1304392959","🇨🇦 CA":"634720426","🇬🇧 UK":"1657555313","🇦🇺 AU":"1871282385","🇪🇺 EU":"975667344"}
C = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
A = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT","BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM","BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid): return pd.read_csv(f"{B}&gid={gid}")

def is_c(s): return any(x in str(s).upper() for x in C)
def is_a(s): return any(x in str(s).upper() for x in A)

pg = st.sidebar.radio("Nav", ["📦 Inv", "💰 Sales"])

# --- INVENTORY ---
if pg == "📦 Inv":
    st.title("📦 Inventory")
    try:
        df = load("0")
        m = st.radio("Market", list(G.keys()), horizontal=True)
        idx = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}[m]
        df_i = df.iloc[:, [0, idx]].copy()
        df_i.columns = ["SKU", "Qty"]
        df_i = df_i.dropna(subset=["SKU"])
        df_i["Qty"] = pd.to_numeric(df_i["Qty"], errors='coerce').fillna(0).astype(int)
        
        c1, c2 = st.columns(2)
        with c1:
            sc = df_i[df_i["SKU"].apply(is_c)]
            st.metric("Cameras", f"{sc['Qty'].sum():,}")
            st.dataframe(sc, hide_index=True)
        with c2:
            sa = df_i[df_i["SKU"].apply(is_a)]
            st.metric("Accessories", f"{sa['Qty'].sum():,}")
            st.dataframe(sa, hide_index=True)
    except Exception as e: st.error(e)

# --- SALES ---
elif pg == "💰 Sales":
    st.title("💰 Sales Performance")
    r = st.sidebar.selectbox("Region", list(G.keys()))
    try:
        df = load(G[r])
        df.columns = [str(c).strip().lower() for c in df.columns]
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df[~df['sku'].str.contains('unknown|worry|delivery', case=False, na=False)]
        
        lt = df['date'].max()
        s1 = lt - timedelta(6)
        p1, p2 = s1 - timedelta(7), s1 - timedelta(1)
        
        cur = df[(df['date'] >= s1) & (df['date'] <= lt)].copy()
        pre = df[(df['date'] >= p1) & (df['date'] <= p2)].copy()
        ytd = df[pd.to_datetime(df['date']).dt.year == lt.year].copy()
        y_sm = ytd.groupby('sku')['quantity'].sum().reset_index()

        st.write(f"Week: {s1} to {lt}")
        c1, c2 = st.columns(2)
        with c1:
            v = cur[cur['sku'].apply(
