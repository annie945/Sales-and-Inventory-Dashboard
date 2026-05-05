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
PO_MASTER_SHEET_ID = "1qaITe6eRrJMY_Z1JdC_la-Z69OiwIlOWbRE6jj7uh0A"

# GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}
GID_3PL_SUMMARY = "972554877" 
GID_PO_GRID = "1801670245"
GIDS_RAW_SHIPPING = {"🇺🇸 US": "215858249", "🇨🇦 CA": "91803080", "🇪🇺 EU": "1062524574"}

SUMMARY_COLS = {
    "🇺🇸 US": {"fulfill": 1, "shipping": 2, "storage": 3},
    "🇨🇦 CA": {"fulfill": 4, "shipping": 5, "storage": 6},
    "🇪🇺 EU": {"fulfill": 10, "shipping": 11, "storage": 12}
}

US_MACRO = {'alabama': 'East', 'alaska': 'West', 'arizona': 'West', 'arkansas': 'Central', 'california': 'West', 'colorado': 'West', 'connecticut': 'East', 'delaware': 'East', 'florida': 'East', 'georgia': 'East', 'hawaii': 'West', 'idaho': 'West', 'illinois': 'Central', 'indiana': 'Central', 'iowa': 'Central', 'kansas': 'Central', 'kentucky': 'East', 'louisiana': 'Central', 'maine': 'East', 'maryland': 'East', 'massachusetts': 'East', 'michigan': 'Central', 'minnesota': 'Central', 'mississippi': 'East', 'missouri': 'Central', 'montana': 'West', 'nebraska': 'Central', 'nevada': 'West', 'new hampshire': 'East', 'new jersey': 'East', 'new mexico': 'West', 'new york': 'East', 'north carolina': 'East', 'north dakota': 'Central', 'ohio': 'Central', 'oklahoma': 'Central', 'oregon': 'West', 'pennsylvania': 'East', 'rhode island': 'East', 'south carolina': 'East', 'south dakota': 'Central', 'tennessee': 'East', 'texas': 'Central', 'utah': 'West', 'vermont': 'East', 'virginia': 'East', 'washington': 'West', 'west virginia': 'East', 'wisconsin': 'Central', 'wyoming': 'West'}
CA_MACRO = {'alberta': 'West', 'british columbia': 'West', 'manitoba': 'West', 'new brunswick': 'East', 'newfoundland and labrador': 'East', 'nova scotia': 'East', 'northwest territories': 'West', 'nunavut': 'West', 'ontario': 'East', 'prince edward island': 'East', 'quebec': 'East', 'saskatchewan': 'West', 'yukon': 'West'}

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def normalize_loc(s, reg):
    if pd.isna(s): return ""
    s = str(s).lower().strip()
    if reg == "🇪🇺 EU":
        eu_map = {'de':'germany', 'fr':'france', 'it':'italy', 'es':'spain', 'nl':'netherlands', 'be':'belgium', 'at':'austria', 'pl':'poland', 'se':'sweden', 'dk':'denmark', 'fi':'finland', 'pt':'portugal', 'ie':'ireland', 'gr':'greece', 'cz':'czech republic', 'ro':'romania', 'hu':'hungry', 'bg':'bulgaria', 'sk':'slovakia', 'hr':'croatia', 'si':'slovenia', 'ee':'estonia', 'lv':'latvia', 'lt':'lithuania', 'cy':'cyprus', 'mt':'malta', 'lu':'luxembourg', 'ch':'switzerland', 'no':'norway', 'gb':'united kingdom', 'uk':'united kingdom'}
        return eu_map.get(s, s)
    return s

def extract_state(val):
    if pd.isna(val): return ""
    v = str(val).upper().strip()
    match = re.search(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b', v)
    return match.group(1).lower() if match else ""

def is_valid_sku(s):
    s = str(s).upper().strip()
    if any(x in s for x in ["NAN", "", "TOTAL", "HEALTH", "RISK", "SHIPPING"]): return False
    return any(x in s for x in ["MA-","MC-","MK-","MP-","MV-","MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"])

def is_cam(s):
    s = str(s).upper().strip()
    if s in ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]: return True
    return any(s.startswith(x) for x in ["MA-","MC-","MK-","MP-","MV-"])

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance", "🚚 3PL Costs & Logistics"]
page = st.sidebar.radio("Dashboard View", menu_options)

# --- 1. INVENTORY & INBOUND ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)

    # Inbound Section
    try:
        st.subheader("🚚 Inbound Pipeline")
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = [str(c).strip().upper() for c in df_po.columns]
        status_col = df_po.columns[-1]
        df_po = df_po[df_po[status_col].astype(str).str.upper() != "RECEIVED"]
        
        region_key = m_sel.split()[-1]
        dest_col = next((c for c in df_po.columns if "DEST" in c), df_po.columns[4])
        df_po_filtered = df_po[df_po[dest_col].astype(str).str.contains(region_key, case=False, na=False)]
        
        if not df_po_filtered.empty:
            st.dataframe(df_po_filtered[['PO NUMBER', 'SKU', 'SHIPPED QTY', 'ETA', 'TRACKING']], hide_index=True)
        else:
            st.info("No incoming shipments for this region.")
    except: st.warning("Could not load Inbound data.")

    # Stock Section
    inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
    df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1: st.subheader("🔴 Out of Stock (OOS)"); st.dataframe(s_df[s_df["Stock"]==0], hide_index=True)
    with c2: st.subheader("🟡 Low Stock (<50)"); st.dataframe(s_df[(s_df["Stock"]>0)&(s_df["Stock"]<50)].sort_values(by="Stock"), hide_index=True)
    
    st.divider()
    st.subheader("📋 Full Inventory List")
    col_a, col_b = st.columns(2)
    with col_a: st.markdown("#### 📸 Cameras"); st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with col_b: st.markdown("#### 🎒 Accessories"); st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)


# --- 2. SALES ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(c).lower().strip() for c in df.columns]
        s_col, q_col, d_col = next(c for c in df.columns if 'sku' in c), next(c for c in df.columns if 'qty' in c or 'quantity' in c), next(c for c in df.columns if 'date' in c)
        
        # Clean Data
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        # STRICT WINDOW
        target_start, target_end = datetime(2026, 4, 27).date(), datetime(2026, 5, 3).date()
        prev_start, prev_end = target_start - timedelta(7), target_start - timedelta(1)
        st.info(f"📍 **Confirmed Window:** April 27 - May 3")
        
        curr_w = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_w = df[(df['clean_date'] >= prev_start) & (df['clean_date'] <= prev_end)]
        
        # SAFE MERGE: Prevents KeyError by ensuring columns exist even if empty
        c_sum = curr_w.groupby(s_col)['quantity'].sum().reset_index()
        p_sum = prev_w.groupby(s_col)['quantity'].sum().reset_index()
        recon = pd.merge(c_sum, p_sum, on=s_col, how='outer', suffixes=('_C', '_P')).fillna(0)
        recon['Diff'] = recon['quantity_C'] - recon['quantity_P']
        
        m1, m2 = st.columns(2)
        with m1: 
            val_c = recon[recon[s_col].apply(is_cam)]['quantity_C'].sum()
            val_p = recon[recon[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("📸 Cameras (Weekly)", f"{int(val_c)} units", delta=int(val_c - val_p))
        with m2: 
            val_c = recon[~recon[s_col].apply(is_cam)]['quantity_C'].sum()
            val_p = recon[~recon[s_col].apply(is_cam)]['quantity_P'].sum()
            st.metric("🎒 Accessories (Weekly)", f"{int(val_c)} units", delta=int(val_c - val_p))
        
        st.divider()
        st.subheader("🚀 Weekly SKU Movers")
        c1, c2 = st.columns(2)
        with c1: 
            st.success("📈 Top 5 Weekly")
            st.dataframe(recon.nlargest(5, 'Diff')[[s_col, 'Diff']].rename(columns={s_col:'SKU'}), hide_index=True, use_container_width=True)
        with c2: 
            st.error("📉 Bottom 5 Weekly")
            st.dataframe(recon.nsmallest(5, 'Diff')[[s_col, 'Diff']].rename(columns={s_col:'SKU'}), hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🏆 YTD {target_end.year} Top & Bottom Sellers")
        ytd = df[pd.to_datetime(df['clean_date']).dt.year == target_end.year].groupby(s_col)['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        if not ytd.empty:
            with y1: 
                st.markdown("#### 🥇 Top 5 Sellers")
                st.dataframe(ytd.nlargest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Units'}), hide_index=True, use_container_width=True)
            with y2: 
                st.markdown("#### 📉 Bottom 5 Sellers")
                st.dataframe(ytd.nsmallest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Units'}), hide_index=True, use_container_width=True)
                
    except Exception as e: st.error(f"Error loading sales data: {e}")

# --- 3. LOGISTICS & REGION ANALYSIS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Region", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    t_sum, t_ship = st.tabs(["📊 Cost Summary", "🗺️ Shipping Region Analysis"])
    
    with t_sum:
        try:
            df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY); df_sum.columns = range(df_sum.shape[1])
            df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce'); df_sum = df_sum.dropna(subset=[0])
            cols = SUMMARY_COLS[reg_3pl]
            for c in [cols["fulfill"], cols["shipping"], cols["storage"]]:
                df_sum[c] = pd.to_numeric(df_sum[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
            monthly = df_sum.groupby(df_sum[0].dt.to_period('M'))[[cols["fulfill"], cols["shipping"], cols["storage"]]].sum()
            latest = monthly.iloc[-1]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Storage Cost", f"{cur}{latest[cols['storage']]:,.2f}")
            c2.metric("Fulfillment Cost", f"{cur}{latest[cols['fulfill']]:,.2f}")
            c3.metric("Shipping Cost", f"{cur}{latest[cols['shipping']]:,.2f}")
            
            st.divider(); st.subheader("📋 Cost Breakdown")
            trend = monthly.iloc[::-1].copy().reset_index()
            trend.columns = ['Month', 'Fulfillment', 'Shipping', 'Storage']
            trend['Month'] = trend['Month'].astype(str)
            st.dataframe(trend.map(lambda x: f"{cur}{x:,.2f}" if isinstance(x, (int, float)) else x), hide_index=True, use_container_width=True)
        except: st.error("Summary cost data unavailable.")

    with t_ship:
        try:
            raw = load_csv(THREE_PL_SHEET_ID, GIDS_RAW_SHIPPING[reg_3pl]); raw.columns = range(raw.shape[1])
            order_col = 12 if reg_3pl == "🇪🇺 EU" else 2
            st.subheader(f"📍 {reg_3pl} Shipping Distribution")
            
            if reg_3pl in ["🇺🇸 US", "🇨🇦 CA"]:
                raw['State'] = raw[4].apply(extract_state)
                raw['Macro'] = raw['State'].map(US_MACRO if reg_3pl=="🇺🇸 US" else CA_MACRO).fillna('Other')
                dist = raw.groupby('Macro')[order_col].nunique().reset_index().rename(columns={order_col:'Orders'})
                
                c1, c2 = st.columns(2)
                with c1: 
                    st.altair_chart(alt.Chart(dist).mark_arc(innerRadius=50).encode(theta='Orders', color='Macro'), use_container_width=True)
                with c2: 
                    dist['%'] = (dist['Orders'] / dist['Orders'].sum()) * 100
                    dist['Percentage'] = dist['%'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(dist[['Macro', 'Orders', 'Percentage']].sort_values(by='Orders', ascending=False), hide_index=True)
            else:
                raw['Country'] = raw[14].apply(lambda x: normalize_loc(x, reg_3pl))
                dist = raw.groupby('Country')[order_col].nunique().reset_index().rename(columns={order_col:'Orders'})
                dist = dist[dist['Country'] != ""] # Remove blanks
                st.dataframe(dist.sort_values(by='Orders', ascending=False), hide_index=True, use_container_width=True)
        except: st.error("Shipping distribution data error.")

# --- END OF FILE ---
