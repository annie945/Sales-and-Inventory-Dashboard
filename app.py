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

GIDS_3PL_SHIPPING = {"🇺🇸 US": "1369957058", "🇨🇦 CA": "332821648", "🇪🇺 EU": "1032280204"}
GIDS_RAW_SHIPPING = {"🇺🇸 US": "215858249", "🇨🇦 CA": "91803080", "🇪🇺 EU": "1062524574"}

# --- MACRO REGION MAPS ---
US_MACRO = {'alabama': 'East', 'alaska': 'West', 'arizona': 'West', 'arkansas': 'Central', 'california': 'West', 'colorado': 'West', 'connecticut': 'East', 'delaware': 'East', 'florida': 'East', 'georgia': 'East', 'hawaii': 'West', 'idaho': 'West', 'illinois': 'Central', 'indiana': 'Central', 'iowa': 'Central', 'kansas': 'Central', 'kentucky': 'East', 'louisiana': 'Central', 'maine': 'East', 'maryland': 'East', 'massachusetts': 'East', 'michigan': 'Central', 'minnesota': 'Central', 'mississippi': 'East', 'missouri': 'Central', 'montana': 'West', 'nebraska': 'Central', 'nevada': 'West', 'new hampshire': 'East', 'new jersey': 'East', 'new mexico': 'West', 'new york': 'East', 'north carolina': 'East', 'north dakota': 'Central', 'ohio': 'Central', 'oklahoma': 'Central', 'oregon': 'West', 'pennsylvania': 'East', 'rhode island': 'East', 'south carolina': 'East', 'south dakota': 'Central', 'tennessee': 'East', 'texas': 'Central', 'utah': 'West', 'vermont': 'East', 'virginia': 'East', 'washington': 'West', 'west virginia': 'East', 'wisconsin': 'Central', 'wyoming': 'West'}
CA_MACRO = {'alberta': 'West', 'british columbia': 'West', 'manitoba': 'West', 'new brunswick': 'East', 'newfoundland and labrador': 'East', 'nova scotia': 'East', 'northwest territories': 'West', 'nunavut': 'West', 'ontario': 'East', 'prince edward island': 'East', 'quebec': 'East', 'saskatchewan': 'West', 'yukon': 'West'}

# --- UTILITIES ---
def normalize_loc(s, reg):
    if pd.isna(s): return ""
    s = str(s).lower().strip()
    if s == 'nan' or s == '': return ""
    if reg == "🇪🇺 EU":
        eu_map = {'de':'germany', 'fr':'france', 'it':'italy', 'es':'spain', 'nl':'netherlands', 'be':'belgium', 'at':'austria', 'pl':'poland', 'se':'sweden', 'dk':'denmark', 'fi':'finland', 'pt':'portugal', 'ie':'ireland', 'gr':'greece', 'cz':'czech republic', 'ro':'romania', 'hu':'hungry', 'bg':'bulgaria', 'sk':'slovakia', 'hr':'croatia', 'si':'slovenia', 'ee':'estonia', 'lv':'latvia', 'lt':'lithuania', 'cy':'cyprus', 'mt':'malta', 'lu':'luxembourg', 'ch':'switzerland', 'no':'norway', 'gb':'united kingdom', 'uk':'united kingdom', 'fra':'france', 'deu':'germany', 'ita':'italy', 'esp':'spain', 'nld':'netherlands', 'gbr':'united kingdom'}
        if s in eu_map: return eu_map[s]
        for name in eu_map.values():
            if name in s: return name
        return s
    return s

def extract_state(val):
    if pd.isna(val): return ""
    v = str(val).upper().strip()
    match = re.search(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b', v)
    if match: return match.group(1).lower()
    return ""

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    noise = ["WORRY FREE", "DELIVERY", "PROTECTION", "NAN", "TOTAL", "HEALTH", "RISK", "ATTENTION", "SKU"]
    if any(x in s for x in noise) or s == "": return False
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
    
    df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

    st.divider()
    col_oos, col_low = st.columns(2)
    with col_oos:
        st.subheader("🔴 Out of Stock (OOS)")
        oos_df = s_df[s_df["Stock"] == 0].copy()
        if not oos_df.empty: st.error(f"{len(oos_df)} SKUs OOS"); st.dataframe(oos_df, hide_index=True, use_container_width=True)
        else: st.success("✅ No SKUs are out of stock.")
    with col_low:
        st.subheader("🟡 Low Stock Warning (<50)")
        low_stock_df = s_df[(s_df["Stock"] > 0) & (s_df["Stock"] < 50)].copy()
        if not low_stock_df.empty: st.warning(f"{len(low_stock_df)} SKUs below 50"); st.dataframe(low_stock_df.sort_values(by="Stock"), hide_index=True, use_container_width=True)
        else: st.success("✅ All active SKUs > 50 units.")

# --- 2. SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        s_col, q_col, d_col = next(c for c in df.columns if 'sku' in c), next(c for c in df.columns if 'qty' in c or 'quantity' in c), next(c for c in df.columns if 'date' in c)
        df = df.rename(columns={s_col: 'sku', q_col: 'quantity', d_col: 'date'})
        df = df[df['sku'].apply(is_valid_sku)]
        df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
        df = df.dropna(subset=['date']); df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        
        lt = df['date'].max(); s_curr, e_curr = lt - timedelta(6), lt
        s_prev, e_prev = s_curr - timedelta(7), s_curr - timedelta(1)
        st.info(f"📍 **{reg}** | Window: {s_curr} to {e_curr}")
        
        curr_week = df[(df['date'] >= s_curr) & (df['date'] <= e_curr)].groupby('sku')['quantity'].sum().reset_index()
        prev_week = df[(df['date'] >= s_prev) & (df['date'] <= e_prev)].groupby('sku')['quantity'].sum().reset_index()
        recon = pd.merge(curr_week, prev_week, on='sku', how='outer', suffixes=('_C', '_P')).fillna(0)
        recon['Diff'] = recon['quantity_C'] - recon['quantity_P']
        
        m1, m2 = st.columns(2)
        with m1: v, o = recon[recon['sku'].apply(is_cam)]['quantity_C'].sum(), recon[recon['sku'].apply(is_cam)]['quantity_P'].sum(); st.metric("📸 Cameras", f"{int(v)}", delta=f"{int(v-o)}")
        with m2: v, o = recon[~recon['sku'].apply(is_cam)]['quantity_C'].sum(), recon[~recon['sku'].apply(is_cam)]['quantity_P'].sum(); st.metric("🎒 Accessories", f"{int(v)}", delta=f"{int(v-o)}")
        
        st.divider()
        st.subheader("🚀 Weekly SKU Movers")
        c1, c2 = st.columns(2)
        with c1: st.success("📈 Top 5 Weekly"); st.dataframe(recon.nlargest(5, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)
        with c2: st.error("📉 Bottom 5 Weekly"); st.dataframe(recon.nsmallest(5, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top & Bottom Sellers")
        ytd = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        with y1: st.markdown("#### 🥇 Top 5 Sellers"); st.dataframe(ytd.nlargest(5, 'quantity'), hide_index=True, use_container_width=True)
        with y2: st.markdown("#### 📉 Bottom 5 Sellers"); st.dataframe(ytd.nsmallest(5, 'quantity'), hide_index=True, use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

# --- 3. 3PL COSTS & LOGISTICS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Select Region for 3PL Data", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    def clean_currency(val):
        if pd.isna(val): return 0.0
        v = str(val).replace('€', '').replace('$', '').replace('£', '').strip()
        if v == '': return 0.0
        if ',' in v and '.' in v: v = v.replace('.', '').replace(',', '.') if v.rfind(',') > v.rfind('.') else v.replace(',', '')
        elif ',' in v: v = v.replace(',', '.') if len(v.split(',')[-1]) in [1,2] else v.replace(',', '')
        v = ''.join(c for c in v if c.isdigit() or c in '.-')
        try: return float(v)
        except: return 0.0

    try:
        df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY)
        df_sum.columns = range(df_sum.shape[1])
        df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
        df_sum = df_sum.dropna(subset=[0]) 
        cols = SUMMARY_COLS[reg_3pl]
        f_col, s_col, st_col = cols["fulfill"], cols["shipping"], cols["storage"]
        for c in [f_col, s_col, st_col]: df_sum[c] = df_sum[c].apply(clean_currency)
        df_sum['YM'] = df_sum[0].dt.to_period('M')
        valid_months_df = df_sum.groupby('YM')[[f_col, s_col, st_col]].sum()
        most_recent_ym = valid_months_df.sum(axis=1)[valid_months_df.sum(axis=1) > 0].index.max()
        df_curr = df_sum[df_sum['YM'] == most_recent_ym]
        
        st.subheader(f"💸 Monthly Overview ({most_recent_ym.strftime('%B %Y')})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Storage Cost", f"{cur}{df_curr[st_col].sum():,.2f}")
        c2.metric("Fulfillment Cost", f"{cur}{df_curr[f_col].sum():,.2f}")
        c3.metric("Shipping Cost", f"{cur}{df_curr[s_col].sum():,.2f}")
        
        st.divider(); st.subheader("📋 Historical Cost Breakdown")
        monthly_trend = valid_months_df.copy().iloc[::-1]
        monthly_trend.columns = ['Fulfillment', 'Shipping', 'Storage']
        monthly_trend.index = monthly_trend.index.astype(str)
        st.dataframe(monthly_trend.map(lambda x: f"{cur}{x:,.2f}"), use_container_width=True)
    except Exception as e: st.error(f"Summary data error: {e}")

# --- END OF FILE ---
