import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import re

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
GID_PO_GRID = "1801670245" 
GID_SAFETY_SOURCE = "2100066410"

# --- 3PL DATA GIDS ---
THREE_PL_SHEET_ID = "1UzHDyqkj1fvGYOXk8e_iOSWYsIofHB7id0hjEaX7Rm4"
GID_3PL_SUMMARY = "972554877" 

SUMMARY_COLS = {
    "🇺🇸 US": {"fulfill": 1, "shipping": 2, "storage": 3},
    "🇨🇦 CA": {"fulfill": 4, "shipping": 5, "storage": 6},
    "🇪🇺 EU": {"fulfill": 10, "shipping": 11, "storage": 12},
    "🇬🇧 UK": {"fulfill": 13, "shipping": 14, "storage": 15}
}

GIDS_3PL_SHIPPING = {
    "🇺🇸 US": "1369957058", 
    "🇨🇦 CA": "332821648", 
    "🇪🇺 EU": "1032280204"
}

GIDS_RAW_SHIPPING = {
    "🇺🇸 US": "215858249",
    "🇨🇦 CA": "91803080", 
    "🇪🇺 EU": "1062524574"
}

# --- UTILITIES ---
@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    if s in ["NAN", "", "TOTAL", "HEALTH", "RISK"]: return False
    return any(x in s for x in ["MA-","MC-","MK-","MP-","MV-","MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"])

def is_cam(s):
    s = str(s).upper().strip()
    if s in ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]: return True
    return any(s.startswith(x) for x in ["MA-","MC-","MK-","MP-","MV-"])

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance", "🚚 3PL Costs & Logistics"]
page = st.sidebar.radio("Dashboard View", menu_options)

# --- SALES PERFORMANCE ---
if page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # 1. Identify Columns
        s_col = next(c for c in df.columns if 'sku' in c)
        q_col = next(c for c in df.columns if 'qty' in c or 'quantity' in c)
        d_col = next(c for c in df.columns if 'date' in c)
        
        # 2. Data Cleaning
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        # 3. Time Windows
        target_end = datetime(2026, 5, 3).date()
        target_start = datetime(2026, 4, 27).date()
        prev_end = target_start - timedelta(days=1)
        prev_start = target_start - timedelta(days=7)
        
        st.info(f"📅 **Weekly Window:** {target_start} to {target_end}")
        
        # 4. Weekly Calculation
        curr_week = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_week = df[(df['clean_date'] >= prev_start) & (df['clean_date'] <= prev_end)]
        
        c_sums = curr_week.groupby(s_col)['quantity'].sum().reset_index()
        p_sums = prev_week.groupby(s_col)['quantity'].sum().reset_index()
        
        res = pd.merge(c_sums, p_sums, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
        res['Diff'] = res['quantity_C'] - res['quantity_P']
        
        # 5. Dashboard Metrics
        m1, m2 = st.columns(2)
        with m1:
            cam_c = res[res[s_col].apply(is_cam)]['quantity_C'].sum()
            cam_p = res[res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("📸 Camera Units (Weekly)", f"{int(cam_c)}", delta=f"{int(cam_c - cam_p)}")
        with m2:
            acc_c = res[~res[s_col].apply(is_cam)]['quantity_C'].sum()
            acc_p = res[~res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("🎒 Accessory Units (Weekly)", f"{int(acc_c)}", delta=f"{int(acc_c - acc_p)}")
            
        # 6. RESTORED YTD TOP SALES
        st.divider()
        curr_year = target_end.year
        st.subheader(f"🏆 YTD {curr_year} Top Rankings (Total Units)")
        
        ytd_df = df[pd.to_datetime(df['clean_date']).dt.year == curr_year]
        ytd_sums = ytd_df.groupby(s_col)['quantity'].sum().reset_index()
        
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top 5 Cameras")
            top_c = ytd_sums[ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_c.rename(columns={s_col:'SKU', 'quantity':'Total Units'}), hide_index=True, use_container_width=True)
        with y2:
            st.markdown("#### 🥇 Top 5 Accessories")
            top_a = ytd_sums[~ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_a.rename(columns={s_col:'SKU', 'quantity':'Total Units'}), hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Sales Data Error: {e}")

# --- INVENTORY & RISK ---
elif page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)
    
    df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

    st.divider()
    col_oos, col_low = st.columns(2)
    with col_oos:
        st.subheader("🔴 Out of Stock (OOS)")
        oos = s_df[s_df["Stock"] == 0]
        st.dataframe(oos, hide_index=True, use_container_width=True)
    with col_low:
        st.subheader("🟡 Low Stock (<50)")
        low = s_df[(s_df["Stock"] > 0) & (s_df["Stock"] < 50)]
        st.dataframe(low.sort_values(by="Stock"), hide_index=True, use_container_width=True)

# --- 3PL COSTS & LOGISTICS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Region", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    try:
        df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY)
        df_sum.columns = range(df_sum.shape[1])
        df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
        df_sum = df_sum.dropna(subset=[0])
        
        cols = SUMMARY_COLS[reg_3pl]
        for c in [cols["fulfill"], cols["shipping"], cols["storage"]]:
            df_sum[c] = pd.to_numeric(df_sum[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
            
        df_sum['YM'] = df_sum[0].dt.to_period('M')
        monthly = df_sum.groupby('YM')[[cols["fulfill"], cols["shipping"], cols["storage"]]].sum()
        
        st.subheader(f"📊 {reg_3pl} Monthly Summary")
        latest = monthly.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Storage", f"{cur}{latest[cols['storage']]:,.2f}")
        c2.metric("Fulfillment", f"{cur}{latest[cols['fulfill']]:,.2f}")
        c3.metric("Shipping", f"{cur}{latest[cols['shipping']]:,.2f}")
        
        st.divider()
        st.subheader("📋 Cost Breakdown")
        disp_table = monthly.copy().iloc[::-1]
        disp_table.index = disp_table.index.astype(str)
        st.dataframe(disp_table.map(lambda x: f"{cur}{x:,.2f}"), use_container_width=True)
    except Exception as e:
        st.error(f"3PL Summary Error: {e}")

# --- END OF FILE ---
