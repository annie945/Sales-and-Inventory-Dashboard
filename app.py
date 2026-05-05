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
MAIN_SHEET_ID = "1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"
THREE_PL_SHEET_ID = "1UzHDyqkj1fvGYOXk8e_iOSWYsIofHB7id0hjEaX7Rm4"

# GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}
GID_3PL_SUMMARY = "972554877" 

SUMMARY_COLS = {
    "🇺🇸 US": {"fulfill": 1, "shipping": 2, "storage": 3},
    "🇨🇦 CA": {"fulfill": 4, "shipping": 5, "storage": 6},
    "🇪🇺 EU": {"fulfill": 10, "shipping": 11, "storage": 12}
}

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

# --- 1. INVENTORY & RISK ---
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
        oos_df = s_df[s_df["Stock"] == 0].copy()
        st.dataframe(oos_df, hide_index=True, use_container_width=True)
    with c_low:
        st.subheader("🟡 Low Stock Warning (<50)")
        low_stock_df = s_df[(s_df["Stock"] > 0) & (s_df["Stock"] < 50)].copy()
        st.dataframe(low_stock_df.sort_values(by="Stock"), hide_index=True, use_container_width=True)

# --- 2. SALES PERFORMANCE ---
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
        
        # IMPROVED DATE HANDLING: Standardize all dates to YYYY-MM-DD
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        target_start = datetime(2026, 4, 27).date()
        target_end = datetime(2026, 5, 3).date()
        
        st.info(f"📊 **Data Range:** {target_start} to {target_end}")
        
        # Use .isin for multiple days to be extremely safe
        week_range = pd.date_range(target_start, target_end).date
        prev_range = pd.date_range(target_start - timedelta(7), target_start - timedelta(1)).date
        
        curr_w = df[df['clean_date'].isin(week_range)]
        prev_w = df[df['clean_date'].isin(prev_range)]
        
        if curr_w.empty:
            st.warning("⚠️ No data found. Please check if the Google Sheet has entries for this date range.")
            st.write(f"Last date found in sheet: {df['clean_date'].max()}")
        else:
            c_sum = curr_w.groupby(s_col)['quantity'].sum().reset_index()
            p_sum = prev_w.groupby(s_col)['quantity'].sum().reset_index()
            res = pd.merge(c_sum, p_sum, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
            
            m1, m2 = st.columns(2)
            with m1:
                val = res[res[s_col].apply(is_cam)]['quantity_C'].sum()
                st.metric("📸 Camera Units", f"{int(val)}", delta=int(val - res[res[s_col].apply(is_cam)]['quantity_P'].sum()))
            with m2:
                val = res[~res[s_col].apply(is_cam)]['quantity_C'].sum()
                st.metric("🎒 Accessory Units", f"{int(val)}", delta=int(val - res[~res[s_col].apply(is_cam)]['quantity_P'].sum()))

        st.divider()
        st.subheader(f"🏆 YTD {target_end.year} Rankings")
        ytd_sums = df[pd.to_datetime(df['clean_date']).dt.year == target_end.year].groupby(s_col)['quantity'].sum().reset_index()
        
        col_top, col_bot = st.columns(2)
        if not ytd_sums.empty:
            with col_top:
                st.markdown("#### 🥇 Top 5 Sellers")
                st.dataframe(ytd_sums.nlargest(5, 'quantity').rename(columns={s_col:'SKU', 'quantity':'Units'}), hide_index=True)
            with col_bot:
                st.markdown("#### 📉 Bottom 5 Sellers")
                st.dataframe(ytd_sums.nsmallest(5, 'quantity').rename(columns={s_col:'SKU', 'quantity':'Units'}), hide_index=True)

    except Exception as e: st.error(f"Sales window error: {e}")

# --- 3. 3PL LOGISTICS ---
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
        
        st.subheader(f"📊 {reg_3pl} Monthly Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Storage Cost", f"{cur}{latest[cols['storage']]:,.2f}")
        c2.metric("Fulfillment Cost", f"{cur}{latest[cols['fulfill']]:,.2f}")
        c3.metric("Shipping Cost", f"{cur}{latest[cols['shipping']]:,.2f}")
        
        st.divider()
        st.subheader("📋 Historical Cost Breakdown")
        trend = monthly.iloc[::-1].copy().reset_index()
        trend.columns = ['Month', 'Fulfillment', 'Shipping', 'Storage']
        trend['Month'] = trend['Month'].astype(str)
        st.dataframe(trend.style.format({c:f'{cur}{{:.2f}}' for c in ['Fulfillment','Shipping','Storage']}), hide_index=True, use_container_width=True)

    except Exception as e: st.error(f"3PL Summary error: {e}")

# --- END OF FILE ---
