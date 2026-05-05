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
SUMMARY_COLS = {"🇺🇸 US": {"fulfill": 1, "shipping": 2, "storage": 3}, "🇨🇦 CA": {"fulfill": 4, "shipping": 5, "storage": 6}, "🇪🇺 EU": {"fulfill": 10, "shipping": 11, "storage": 12}}
GIDS_RAW_SHIPPING = {"🇺🇸 US": "215858249", "🇨🇦 CA": "91803080", "🇪🇺 EU": "1062524574"}

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    if any(x in s for x in ["NAN", "", "TOTAL", "HEALTH", "RISK", "SHIPPING", "PROTECTION"]): return False
    return any(x in s for x in ["MA-","MC-","MK-","MP-","MV-","MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"])

def is_cam(s):
    s = str(s).upper().strip()
    if s in ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]: return True
    return any(s.startswith(x) for x in ["MA-","MC-","MK-","MP-","MV-"])

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance", "🚚 3PL Costs & Logistics"]
page = st.sidebar.radio("Dashboard View", menu_options)

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)
    inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
    df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    st.divider()
    c_oos, c_low = st.columns(2)
    with c_oos:
        st.subheader("🔴 Out of Stock (OOS)")
        st.dataframe(s_df[s_df["Stock"] == 0], hide_index=True, use_container_width=True)
    with c_low:
        st.subheader("🟡 Low Stock Warning (<50)")
        st.dataframe(s_df[(s_df["Stock"] > 0) & (s_df["Stock"] < 50)].sort_values(by="Stock"), hide_index=True, use_container_width=True)
    st.divider()
    st.subheader("📋 Full Inventory List")
    col_a, col_b = st.columns(2)
    with col_a: st.markdown("#### 📸 Cameras"); st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True)
    with col_b: st.markdown("#### 🎒 Accessories"); st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True)

# --- SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        s_col = next(c for c in df.columns if 'sku' in c)
        q_col = next(c for c in df.columns if 'qty' in c or 'quantity' in c)
        d_col = next(c for c in df.columns if 'date' in c)
        
        # CLEAN DATA: Convert quantity to numeric and date to pure date objects (no time)
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        df = df[df['quantity'] > 0] # Filter out returns or cancellations

        # STRICT WEEKLY WINDOW: 4/27 (Monday) to 5/3 (Sunday)
        target_start = datetime(2026, 4, 27).date()
        target_end = datetime(2026, 5, 3).date()
        prev_start = target_start - timedelta(days=7)
        prev_end = target_start - timedelta(days=1)
        
        st.info(f"📅 **Audit Window:** Monday, April 27 to Sunday, May 3")
        
        curr_w = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_w = df[(df['clean_date'] >= prev_start) & (df['clean_date'] <= prev_end)]
        
        c_sum = curr_w.groupby(s_col)['quantity'].sum().reset_index()
        p_sum = prev_w.groupby(s_col)['quantity'].sum().reset_index()
        res = pd.merge(c_sum, p_sum, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
        
        m1, m2 = st.columns(2)
        with m1:
            val_c = res[res[s_col].apply(is_cam)]['quantity_C'].sum()
            val_p = res[res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("📸 Cameras (Weekly)", f"{int(val_c)} units", delta=int(val_c - val_p))
        with m2:
            val_c = res[~res[s_col].apply(is_cam)]['quantity_C'].sum()
            val_p = res[~res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("🎒 Accessories (Weekly)", f"{int(val_c)} units", delta=int(val_c - val_p))

        st.divider()
        st.subheader(f"🏆 YTD {target_end.year} Top Sellers (Units)")
        ytd_df = df[pd.to_datetime(df['clean_date']).dt.year == target_end.year]
        ytd_sums = ytd_df.groupby(s_col)['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top Cameras")
            st.dataframe(ytd_sums[ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Qty'}), hide_index=True)
        with y2:
            st.markdown("#### 🥇 Top Accessories")
            st.dataframe(ytd_sums[~ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Qty'}), hide_index=True)
    except Exception as e: st.error(f"Sales error: {e}")

# --- 3PL COSTS ---
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
        latest = monthly.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Storage", f"{cur}{latest[cols['storage']]:,.2f}"); c2.metric("Fulfillment", f"{cur}{latest[cols['fulfill']]:,.2f}"); c3.metric("Shipping", f"{cur}{latest[cols['shipping']]:,.2f}")
        st.divider(); st.subheader("📋 Cost Breakdown")
        st.dataframe(monthly.iloc[::-1].copy().reset_index().rename(columns={cols['fulfill']:'Fulfillment', cols['shipping']:'Shipping', cols['storage']:'Storage'}).style.format({c:f'{cur}{{:.2f}}' for c in ['Fulfillment','Shipping','Storage']}))
    except Exception as e: st.error(f"3PL error: {e}")

# --- END OF FILE ---
