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
        return eu_map.get(s, s)
    elif reg == "🇺🇸 US":
        us_map = {'al':'alabama', 'ak':'alaska', 'az':'arizona', 'ar':'arkansas', 'ca':'california', 'co':'colorado', 'ct':'connecticut', 'de':'delaware', 'fl':'florida', 'ga':'georgia', 'hi':'hawaii', 'id':'idaho', 'il':'illinois', 'in':'indiana', 'ia':'iowa', 'ks':'kansas', 'ky':'kentucky', 'la':'louisiana', 'me':'maine', 'md':'maryland', 'ma':'massachusetts', 'mi':'michigan', 'mn':'minnesota', 'ms':'mississippi', 'mo':'missouri', 'mt':'montana', 'ne':'nebraska', 'nv':'nevada', 'nh':'new hampshire', 'nj':'new jersey', 'nm':'new mexico', 'ny':'new york', 'nc':'north carolina', 'nd':'north dakota', 'oh':'ohio', 'ok':'oklahoma', 'or':'oregon', 'pa':'pennsylvania', 'ri':'rhode island', 'sc':'south carolina', 'sd':'south dakota', 'tn':'tennessee', 'tx':'texas', 'ut':'utah', 'vt':'vermont', 'va':'virginia', 'wa':'washington', 'wv':'west virginia', 'wi':'wisconsin', 'wy':'wyoming'}
        return us_map.get(s, s)
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
    return any(x in s for x in ["MA-","MC-","MK-","MP-","MV-","MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"])

def is_cam(s):
    s = str(s).upper().strip()
    if s in ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]: return True
    return any(s.startswith(x) for x in ["MA-","MC-","MK-","MP-","MV-"])

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance", "🚚 3PL Costs & Logistics"]
page = st.sidebar.radio("Dashboard View", menu_options)

# --- SALES PERFORMANCE (REWRITTEN FOR DATE ACCURACY) ---
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
        
        # 2. Hard Date Conversion
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df.dropna(subset=['clean_date', q_col])
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        # 3. SET STRICT WEEKLY WINDOWS
        # Current Week: April 27 (Monday) to May 3 (Sunday)
        target_end = datetime(2026, 5, 3).date()
        target_start = datetime(2026, 4, 27).date()
        
        # Previous Week: April 20 to April 26
        prev_end = target_start - timedelta(days=1)
        prev_start = target_start - timedelta(days=7)
        
        st.info(f"📅 **Confirmed Window:** {target_start} to {target_end}")
        
        # 4. Filter & Aggregate
        curr_df = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_df = df[(df['clean_date'] >= prev_start) & (df['clean_date'] <= prev_end)]
        
        curr_sums = curr_df.groupby(s_col)['quantity'].sum().reset_index()
        prev_sums = prev_df.groupby(s_col)['quantity'].sum().reset_index()
        
        res = pd.merge(curr_sums, prev_sums, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
        res['Diff'] = res['quantity_C'] - res['quantity_P']
        
        # 5. Metrics
        m1, m2 = st.columns(2)
        with m1:
            cam_val = res[res[s_col].apply(is_cam)]['quantity_C'].sum()
            cam_prev = res[res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("📸 Camera Units", f"{int(cam_val)}", delta=f"{int(cam_val - cam_prev)}")
        with m2:
            acc_val = res[~res[s_col].apply(is_cam)]['quantity_C'].sum()
            acc_prev = res[~res[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("🎒 Accessory Units", f"{int(acc_val)}", delta=f"{int(acc_val - acc_prev)}")
            
        st.divider()
        st.subheader("🚀 Top Weekly Movers")
        c1, c2 = st.columns(2)
        with c1:
            st.success("📸 Top Cameras")
            st.dataframe(res[res[s_col].apply(is_cam)].nlargest(5, 'quantity_C')[[s_col, 'quantity_C']].rename(columns={s_col:'SKU', 'quantity_C':'Qty'}), hide_index=True, use_container_width=True)
        with c2:
            st.success("🎒 Top Accessories")
            st.dataframe(res[~res[s_col].apply(is_cam)].nlargest(5, 'quantity_C')[[s_col, 'quantity_C']].rename(columns={s_col:'SKU', 'quantity_C':'Qty'}), hide_index=True, use_container_width=True)

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

# --- 3PL COSTS & LOGISTICS (STABLE VERSION) ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Region", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    try:
        df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY)
        df_sum.columns = range(df_sum.shape[1])
        df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
        df_sum = df_sum.dropna(subset=[0])
        
        # Clean currency
        cols = SUMMARY_COLS[reg_3pl]
        for c in [cols["fulfill"], cols["shipping"], cols["storage"]]:
            df_sum[c] = df_sum[c].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df_sum[c] = pd.to_numeric(df_sum[c], errors='coerce').fillna(0)
            
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
