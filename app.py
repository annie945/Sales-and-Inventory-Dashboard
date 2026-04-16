import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; font-weight: bold; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 5px; }
    h3 { padding-top: 1rem; margin-bottom: 0.5rem; border-bottom: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

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

# --- CATEGORY DEFINITIONS ---
CAMS = ["MA-","MC-","MK-","MP-","MV-"]
ACCS = ["MP2-","MICROSD","TML-","BAG-","LANYARD", "PAPER"]

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    noise = ["WORRY FREE", "DELIVERY", "PROTECTION", "NAN", "TOTAL", "HEALTH", "RISK", "ATTENTION", "SKU"]
    if any(x in s for x in noise) or s == "": return False
    return any(x in s for x in CAMS + ACCS)

def is_cam(s):
    s = str(s).upper()
    if "PAPER" in s: return False # Move paper to accessories
    return any(s.startswith(x) for x in CAMS)

def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = range(df_po.shape[1])
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        region_map = {"🇺🇸 US": ["US"], "🇨🇦 CA": ["CA"], "🇬🇧 UK": ["UK"], "🇦🇺 AU": ["AU"], "🇪🇺 EU": ["EU", "GERMANY"]}
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
st.sidebar.title("🛠️ Controls")
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
page = st.sidebar.radio("Dashboard View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- PAGE 1: INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Pipeline & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Region Selection", list(m_map.keys()), horizontal=True)
    
    df_po = get_filtered_po_data(chan, m_sel)
    if not df_po.empty:
        st.subheader("🚚 Active Inbound Orders")
        st.dataframe(df_po, use_container_width=True, hide_index=True)
    
    st.divider()
    
    df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📸 Camera Stock")
        st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with col_b:
        st.subheader("🎒 Accessory Stock")
        st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

# --- PAGE 2: SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        s_col = next((c for c in df.columns if 'sku' in c), 'sku')
        q_col = next((c for c in df.columns if 'qty' in c or 'quantity' in c), 'quantity')
        d_col = next((c for c in df.columns if 'date' in c), 'date')
        df = df.rename(columns={s_col: 'sku', q_col: 'quantity', d_col: 'date'})
        
        df = df[df['sku'].apply(is_valid_sku)]
        df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
        df = df.dropna(subset=['date'])
        
        lt = df['date'].max()
        s1, p1, p2 = lt - timedelta(6), lt - timedelta(13), lt - timedelta(7)
        curr, prev = df[df['date'] >= s1], df[(df['date'] >= p1) & (df['date'] <= p2)]
        
        st.markdown(f"### 📅 Weekly Snapshot: {s1} to {lt}")
        m1, m2 = st.columns(2)
        with m1:
            v, o = curr[curr['sku'].apply(is_cam)]['quantity'].sum(), prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Camera Units", f"{int(v):,}", delta=f"{int(v-o)}")
        with m2:
            v, o = curr[~curr['sku'].apply(is_cam)]['quantity'].sum(), prev[~prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("🎒 Accessory Units", f"{int(v):,}", delta=f"{int(v-o)}")
        
        st.divider()
        st.subheader("🚀 Weekly Movers (Top 3 & Bottom 3)")
        r_s, p_s = curr.groupby('sku')['quantity'].sum(), prev.groupby('sku')['quantity'].sum()
        cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        cp['Change'] = cp['quantity_c'] - cp['quantity_p']
        cp = cp[cp['quantity_c'] > 0] 
        
        cam_mv, acc_mv = cp[cp.index.map(is_cam)], cp[~cp.index.map(is_cam)]
        
        grid_a, grid_b = st.columns(2)
        with grid_a:
            st.markdown("#### 📸 Camera Movers")
            st.success("Top 3 Increase")
            st.dataframe(cam_mv[cam_mv['Change']>0].nlargest(3, 'Change')[['Change']], use_container_width=True)
            st.error("Bottom 3 Decrease")
            st.dataframe(cam_mv[cam_mv['Change']<0].nsmallest(3, 'Change')[['Change']], use_container_width=True)
        with grid_b:
            st.markdown("#### 🎒 Accessory Movers")
            st.success("Top 3 Increase")
            st.dataframe(acc_mv[acc_mv['Change']>0].nlargest(3, 'Change')[['Change']], use_container_width=True)
            st.error("Bottom 3 Decrease")
            st.dataframe(acc_mv[acc_mv['Change']<0].nsmallest(3, 'Change')[['Change']], use_container_width=True)
            
        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top 5 Rankings")
        ytd_df = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()
        ytd_df.columns = ['SKU', 'Units']
        
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top 5 Cameras (YTD)")
            top_c = ytd_df[ytd_df['SKU'].apply(is_cam)].nlargest(5, 'Units')
            st.dataframe(top_c, hide_index=True, use_container_width=True)
            st.write(f"**Total Units:** {int(top_c['Units'].sum()):,}")
        with y2:
            st.markdown("#### 🥇 Top 5 Accessories (YTD)")
            top_a = ytd_df[~ytd_df['SKU'].apply(is_cam)].nlargest(5, 'Units')
            st.dataframe(top_a, hide_index=True, use_container_width=True)
            st.write(f"**Total Units:** {int(top_a['Units'].sum()):,}")

    except Exception as e:
        st.error(f"Error processing sales data: {e}")
