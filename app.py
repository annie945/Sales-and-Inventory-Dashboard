import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")

# --- IDs ---
FORECAST_SHEET_ID = "1elePyM-HdtFc382VsSac8PD4NQrUSXZF9qypCzyzcCc" 
MAIN_SHEET_ID = "1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
PO_MASTER_SHEET_ID = "1qaITe6eRrJMY_Z1JdC_la-Z69OiwIlOWbRE6jj7uh0A" 

# GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}
GIDS_FOR_MONTHS = {
    "Shopify/WH": {"🇺🇸 US": "2053646844", "🇨🇦 CA": "1132992902", "🇪🇺 EU": "314290170", "🇦🇺 AU": "592032183", "🇬🇧 UK": "1664038544"},
    "Amazon (FBA)": {"🇺🇸 US": "1911531717", "🇨🇦 CA": "749217991"}
}
GID_SAFETY_SOURCE = "2100066410"
GID_PO_GRID = "1801670245" 

CAMS = ["MA-","MC-","MK-","MP-","MV-"]
ACCS = ["MP2-","MICROSD","TML-","BAG-","LANYARD"]

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    if s == "" or "NAN" in s: return False
    return any(x in s for x in CAMS + ACCS)

def is_cam(s): return any(x in str(s).upper() for x in CAMS)

# --- INBOUND PO LOGIC ---
def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = range(df_po.shape[1])
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        
        # Region Mapping
        region_map = {
            "🇺🇸 US": ["US"], "🇨🇦 CA": ["CA"], "🇬🇧 UK": ["UK"], 
            "🇦🇺 AU": ["AU", "NZ"], "🇪🇺 EU": ["EU", "Germany", "France", "NL"]
        }
        keywords = region_map.get(region_label, [])
        
        if channel == "Amazon (FBA)":
            df_po = df_po[df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
        else:
            df_po = df_po[~df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
            
        pattern = '|'.join(keywords)
        df_po = df_po[df_po[4].astype(str).str.contains(pattern, case=False, na=False)]
        return df_po[[0, 5, 6, 9, 10]].rename(columns={0:'PO', 5:'SKU', 6:'Qty', 9:'ETA', 10:'Tracking'})
    except: return pd.DataFrame()

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Channel", ["Shopify/WH", "Amazon (FBA)"])
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)
    
    # Inbound Section
    df_po = get_filtered_po_data(chan, m_sel)
    if not df_po.empty:
        st.subheader("🚚 Inbound Pipeline")
        st.dataframe(df_po, use_container_width=True, hide_index=True)
    
    # Inventory Section
    inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
    df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📸 Cameras")
        st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with c2:
        st.subheader("🎒 Accessories")
        st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

# --- SALES PERFORMANCE (FULL RESTORATION) ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Standardize columns
        s_col = next((c for c in df.columns if 'sku' in c), 'sku')
        q_col = next((c for c in df.columns if 'qty' in c or 'quantity' in c), 'quantity')
        d_col = next((c for c in df.columns if 'date' in c), 'date')
        df = df.rename(columns={s_col: 'sku', q_col: 'quantity', d_col: 'date'})
        
        df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
        df = df.dropna(subset=['date'])
        
        # Time Windows
        lt = df['date'].max()
        s1, p1, p2 = lt - timedelta(6), lt - timedelta(13), lt - timedelta(7)
        curr = df[df['date'] >= s1].copy()
        prev = df[(df['date'] >= p1) & (df['date'] <= p2)].copy()
        
        # Metrics
        st.info(f"📅 Comparing Week: {s1} to {lt} vs Previous Week")
        col1, col2 = st.columns(2)
        with col1:
            v = curr[curr['sku'].apply(is_cam)]['quantity'].sum()
            o = prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Weekly Cameras", int(v), delta=int(v-o))
        with col2:
            v = curr[~curr['sku'].apply(is_cam)]['quantity'].sum()
            o = prev[~prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("🎒 Weekly Accessories", int(v), delta=int(v-o))

        # Top Movers
        st.divider()
        st.subheader("🔥 Weekly Top Movers")
        r_s = curr.groupby('sku')['quantity'].sum()
        p_s = prev.groupby('sku')['quantity'].sum()
        cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        cp['D'] = cp['quantity_c'] - cp['quantity_p']
        
        m1, m2 = st.columns(2)
        with m1:
            st.success("📈 Sales Increase")
            st.dataframe(cp[cp['D'] > 0].nlargest(5, 'D')[['D']], use_container_width=True)
        with m2:
            st.error("📉 Sales Decrease")
            st.dataframe(cp[cp['D'] < 0].nsmallest(5, 'D')[['D']], use_container_width=True)

        # YTD
        st.divider()
        ytd_df = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()
        st.subheader(f"🏆 YTD {lt.year} Top Sellers")
        st.dataframe(ytd_df.nlargest(10, 'quantity'), hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading sales: {e}. Check if the tab for {reg} contains valid 'date' and 'sku' columns.")
