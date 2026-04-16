import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Visual Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Sales")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #1f77b4; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

BASE = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"

# Configuration
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}

CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
ACCS = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT","BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM","BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid): return pd.read_csv(f"{BASE}&gid={gid}")

def is_cam(s): return any(x in str(s).upper() for x in CAMS)
def is_acc(s): return any(x in str(s).upper() for x in ACCS)

# --- SIDEBAR ---
st.sidebar.header("🏢 Channel Select")
channel = st.sidebar.selectbox("Source", ["Shopify/WH", "Amazon (FBA)"])

st.sidebar.header("📌 Category")
page = st.sidebar.radio("View", ["📦 Inventory", "💰 Sales Performance"])

# --- INVENTORY ---
if page == "📦 Inventory":
    st.title(f"📦 {channel} Inventory")
    try:
        if channel == "Amazon (FBA)":
            df = load("856174189")
            m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18}
            markets = ["🇺🇸 US", "🇨🇦 CA", "🇬🇧 UK", "🇦🇺 AU"]
        else:
            df = load("0")
            m_map = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
            markets = list(GIDS_ORIG.keys())

        m_label = st.radio("Market", markets, horizontal=True)
        sku_df = df.iloc[:, [0, m_map[m_label]]].copy()
        sku_df.columns = ["SKU", "Stock"]
        sku_df = sku_df.dropna(subset=["SKU"])
        sku_df["Stock"] = pd.to_numeric(sku_df["Stock"], errors='coerce').fillna(0).astype(int)

        c1, c2 = st.columns(2)
        with c1:
            sub_c = sku_df[sku_df["SKU"].apply(is_cam)]
            st.metric("Total Cameras", f"{sub_c['Stock'].sum():,}")
            st.dataframe(sub_c, hide_index=True, use_container_width=True)
        with c2:
            sub_a = sku_df[sku_df["SKU"].apply(is_acc)]
            st.metric("Total Accessories", f"{sub_a['Stock'].sum():,}")
            st.dataframe(sub_a, hide_index=True, use_container_width=True)
    except Exception as e: st.error(f"Inventory Error: {e}")

# --- SALES ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {channel} Sales")
    current_gids = GIDS_AMZ if channel == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(current_gids.keys()))
    
    try:
        df = load(current_gids[reg])
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        s_col = next((c for c in df.columns if 'sku' in c), None)
        q_col = next((c for c in df.columns if 'qty' in c or 'quantity' in c), None)
        d_col = next((c for c in df.columns if 'date' in c), None)

        if not s_col or not q_col or not d_col:
            st.error(f"Missing columns! Found: {list(df.columns)}")
        else:
            df = df.rename(columns={s_col: 'sku', q_col: 'quantity', d_col: 'date'})
            
            # --- FIXED DATE LOGIC FOR AU ERROR ---
            df['date'] = pd.to_datetime(df['date'], format='mixed').dt.date
            
            df = df[~df['sku'].str.contains('unknown|worry|delivery', case=False, na=False)]
            lt = df['date'].max()
            s1, p1, p2 = lt - timedelta(6), lt - timedelta(13), lt - timedelta(7)

            curr = df[(df['date'] >= s1) & (df['date'] <= lt)].copy()
            prev = df[(df['date'] >= p1) & (df['date'] <= p2)].copy()
            y_sm = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()

            st.info(f"📅 Week: {s1} to {lt} vs {p1} to {p2}")
            col1, col2 = st.columns(2)
            with col1:
                v = curr[curr['sku'].apply(is_cam)]['quantity'].sum()
                o = prev[prev['sku'].apply(is_cam)]['quantity'].sum()
                st.metric("📸 Weekly Camera Units", int(v), delta=int(v-o))
            with col2:
                v = curr[curr['sku'].apply(is_acc)]['quantity'].sum()
                o = prev[prev['sku'].apply(is_acc)]['quantity'].sum()
                st.metric("🎒 Weekly Accessory Units", int(v), delta=int(v-o))

            st.divider()
            st.subheader("🔥 Weekly Top Movers")
            r_s, p_s = curr.groupby('sku')['quantity'].sum(), prev.groupby('sku')['quantity'].sum()
            cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
            cp['Delta'] = cp['quantity_c'] - cp['quantity_p']
            
            m1, m2, m3, m4 = st.columns(4)
            cm, ac = cp[cp.index.map(is_cam)], cp[cp.index.map(is_acc)]
            with m1:
                st.success("📈 Cam Inc")
                st.dataframe(cm[cm['Delta']>0].nlargest(3,'Delta')[['Delta']], use_container_width=True)
            with m2:
                st.error("📉 Cam Dec")
                st.dataframe(cm[cm['Delta']<0].nsmallest(3,'Delta')[['Delta']], use_container_width=True)
            with m3:
                st.success("📈 Acc Inc")
                st.dataframe(ac[ac['Delta']>0].nlargest(3,'Delta')[['Delta']], use_container_width=True)
            with m4:
                st.error("📉 Acc Dec")
                st.dataframe(ac[ac['Delta']<0].nsmallest(3,'Delta')[['Delta']], use_container_width=True)

            st.divider()
            st.subheader(f"🏆 YTD {lt.year} Top Sellers")
            y1, y2 = st.columns(2)
            with y1:
                st.info("📸 Camera Top 3 (YTD)")
                st.dataframe(y_sm[y_sm['sku'].apply(is_cam)].nlargest(3,'quantity'), hide_index=True, use_container_width=True)
            with y2:
                st.info("🎒 Accessory Top 3 (YTD)")
                st.dataframe(y_sm[y_sm['sku'].apply(is_acc)].nlargest(3,'quantity'), hide_index=True, use_container_width=True)
    except Exception as e: st.error(f"Sales Error: {e}")
