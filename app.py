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
GIDS_3PL_SHIPPING = {"🇺🇸 US": "1369957058", "🇨🇦 CA": "332821648", "🇪🇺 EU": "1032280204"}
GIDS_RAW_SHIPPING = {"🇺🇸 US": "215858249", "🇨🇦 CA": "91803080", "🇪🇺 EU": "1062524574"}

# --- MACRO REGIONS ---
US_MACRO = {'alabama': 'East', 'alaska': 'West', 'arizona': 'West', 'arkansas': 'Central', 'california': 'West', 'colorado': 'West', 'connecticut': 'East', 'delaware': 'East', 'florida': 'East', 'georgia': 'East', 'hawaii': 'West', 'idaho': 'West', 'illinois': 'Central', 'indiana': 'Central', 'iowa': 'Central', 'kansas': 'Central', 'kentucky': 'East', 'louisiana': 'Central', 'maine': 'East', 'maryland': 'East', 'massachusetts': 'East', 'michigan': 'Central', 'minnesota': 'Central', 'mississippi': 'East', 'missouri': 'Central', 'montana': 'West', 'nebraska': 'Central', 'nevada': 'West', 'new hampshire': 'East', 'new jersey': 'East', 'new mexico': 'West', 'new york': 'East', 'north carolina': 'East', 'north dakota': 'Central', 'ohio': 'Central', 'oklahoma': 'Central', 'oregon': 'West', 'pennsylvania': 'East', 'rhode island': 'East', 'south carolina': 'East', 'south dakota': 'Central', 'tennessee': 'East', 'texas': 'Central', 'utah': 'West', 'vermont': 'East', 'virginia': 'East', 'washington': 'West', 'west virginia': 'East', 'wisconsin': 'Central', 'wyoming': 'West'}
CA_MACRO = {'alberta': 'West', 'british columbia': 'West', 'manitoba': 'West', 'new brunswick': 'East', 'newfoundland and labrador': 'East', 'nova scotia': 'East', 'northwest territories': 'West', 'nunavut': 'West', 'ontario': 'East', 'prince edward island': 'East', 'quebec': 'East', 'saskatchewan': 'West', 'yukon': 'West'}

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    if s in ["NAN", "", "TOTAL", "HEALTH", "RISK", "SHIPPING"]: return False
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
    
    # Load Master Stock
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
        oos = s_df[s_df["Stock"] == 0]
        st.dataframe(oos, hide_index=True, use_container_width=True)
    with c_low:
        st.subheader("🟡 Low Stock (<50)")
        low = s_df[(s_df["Stock"] > 0) & (s_df["Stock"] < 50)]
        st.dataframe(low.sort_values(by="Stock"), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("📋 Full Inventory List")
    col_a, col_b = st.columns(2)
    with col_a: st.markdown("#### 📸 Cameras"); st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True)
    with col_b: st.markdown("#### 🎒 Accessories"); st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True)

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
        
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        # Windows
        target_start, target_end = datetime(2026, 4, 27).date(), datetime(2026, 5, 3).date()
        st.info(f"📅 Weekly Window: {target_start} to {target_end}")
        
        curr_w = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_w = df[(df['clean_date'] >= (target_start - timedelta(7))) & (df['clean_date'] <= (target_start - timedelta(1)))]
        
        c_sum = curr_w.groupby(s_col)['quantity'].sum().reset_index()
        p_sum = prev_w.groupby(s_col)['quantity'].sum().reset_index()
        res = pd.merge(c_sum, p_sum, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
        
        m1, m2 = st.columns(2)
        with m1:
            val = res[res[s_col].apply(is_cam)]['quantity_C'].sum()
            st.metric("📸 Camera Units (Weekly)", f"{int(val)}", delta=int(val - res[res[s_col].apply(is_cam)]['quantity_P'].sum()))
        with m2:
            val = res[~res[s_col].apply(is_cam)]['quantity_C'].sum()
            st.metric("🎒 Accessory Units (Weekly)", f"{int(val)}", delta=int(val - res[~res[s_col].apply(is_cam)]['quantity_P'].sum()))

        st.divider()
        st.subheader(f"🏆 YTD {target_end.year} Top Units")
        ytd_sums = df[pd.to_datetime(df['clean_date']).dt.year == target_end.year].groupby(s_col)['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top Cameras")
            st.dataframe(ytd_sums[ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity'), hide_index=True)
        with y2:
            st.markdown("#### 🥇 Top Accessories")
            st.dataframe(ytd_sums[~ytd_sums[s_col].apply(is_cam)].nlargest(5, 'quantity'), hide_index=True)
    except Exception as e: st.error(f"Sales error: {e}")

# --- 3. 3PL LOGISTICS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Region", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    try:
        # Summary Costs
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
        c1.metric("Storage", f"{cur}{latest[cols['storage']]:,.2f}")
        c2.metric("Fulfillment", f"{cur}{latest[cols['fulfill']]:,.2f}")
        c3.metric("Shipping", f"{cur}{latest[cols['shipping']]:,.2f}")
        
        st.divider()
        st.subheader("📋 Cost Breakdown")
        st.dataframe(monthly.iloc[::-1].copy().reset_index().rename(columns={cols['fulfill']:'Fulfillment', cols['shipping']:'Shipping', cols['storage']:'Storage'}).style.format({c:f'{cur}{{:.2f}}' for c in ['Fulfillment','Shipping','Storage']}))

        # Shipping Distribution
        if reg_3pl in ["🇺🇸 US", "🇨🇦 CA"]:
            st.divider(); st.subheader("🗺️ Regional Distribution (Weekly Window)")
            raw = load_csv(THREE_PL_SHEET_ID, GIDS_RAW_SHIPPING[reg_3pl])
            raw.columns = range(raw.shape[1])
            raw['Date'] = pd.to_datetime(raw[1 if reg_3pl=="🇨🇦 CA" else 0], errors='coerce').dt.date
            # Using same window
            raw_w = raw[(raw['Date'] >= datetime(2026,4,27).date()) & (raw['Date'] <= datetime(2026,5,3).date())]
            
            def map_loc(val):
                v = str(val).lower()
                match = re.search(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b', v.upper())
                code = match.group(1).lower() if match else v
                return (US_MACRO if reg_3pl=="🇺🇸 US" else CA_MACRO).get(code, 'Other')

            raw_w['Region'] = raw_w[4].apply(map_loc)
            dist = raw_w.groupby('Region')[2].nunique().reset_index().rename(columns={2:'Orders'})
            st.altair_chart(alt.Chart(dist).mark_arc(innerRadius=50).encode(theta='Orders', color='Region'), use_container_width=True)
            st.dataframe(dist, hide_index=True)

    except Exception as e: st.error(f"3PL error: {e}")

# --- END OF FILE ---
