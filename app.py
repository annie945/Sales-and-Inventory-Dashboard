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
GID_SAFETY_SOURCE = "2100066410"
GID_PO_GRID = "1801670245" 

# --- NEW 3PL DATA GIDS & MAPPINGS ---
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

REGION_RANGES = {
    "Shopify/WH": {"🇺🇸 US": (1, 21), "🇨🇦 CA": (22, 42), "🇬🇧 UK": (44, 64), "🇪🇺 EU": (66, 86), "🇦🇺 AU": (88, 108)},
    "Amazon (FBA)": {"🇺🇸 US": (110, 130), "🇨🇦 CA": (131, 151)}
}

CAMS_PREFIX = ["MA-","MC-","MK-","MP-","MV-"]
MP2_CAMS = ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]
ACCS_KEYWORDS = ["MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"]

# --- MACRO REGION MAPS ---
US_MACRO = {
    'alabama': 'East', 'alaska': 'West', 'arizona': 'West', 'arkansas': 'Central', 'california': 'West',
    'colorado': 'West', 'connecticut': 'East', 'delaware': 'East', 'florida': 'East', 'georgia': 'East',
    'hawaii': 'West', 'idaho': 'West', 'illinois': 'Central', 'indiana': 'Central', 'iowa': 'Central',
    'kansas': 'Central', 'kentucky': 'East', 'louisiana': 'Central', 'maine': 'East', 'maryland': 'East',
    'massachusetts': 'East', 'michigan': 'Central', 'minnesota': 'Central', 'mississippi': 'East', 'missouri': 'Central',
    'montana': 'West', 'nebraska': 'Central', 'nevada': 'West', 'new hampshire': 'East', 'new jersey': 'East',
    'new mexico': 'West', 'new york': 'East', 'north carolina': 'East', 'north dakota': 'Central', 'ohio': 'Central',
    'oklahoma': 'Central', 'oregon': 'West', 'pennsylvania': 'East', 'rhode island': 'East', 'south carolina': 'East',
    'south dakota': 'Central', 'tennessee': 'East', 'texas': 'Central', 'utah': 'West', 'vermont': 'East',
    'virginia': 'East', 'washington': 'West', 'west virginia': 'East', 'wisconsin': 'Central', 'wyoming': 'West'
}

CA_MACRO = {
    'alberta': 'West', 'british columbia': 'West', 'manitoba': 'West', 'new brunswick': 'East',
    'newfoundland and labrador': 'East', 'nova scotia': 'East', 'northwest territories': 'West',
    'nunavut': 'West', 'ontario': 'East', 'prince edward island': 'East', 'quebec': 'East',
    'saskatchewan': 'West', 'yukon': 'West'
}

# --- UNIVERSAL LOCATION TRANSLATOR ---
def normalize_loc(s, reg):
    if pd.isna(s): return ""
    s = str(s).lower().strip()
    if s == 'nan' or s == '': return ""
    
    if reg == "🇪🇺 EU":
        eu_map = {
            'de':'germany', 'fr':'france', 'it':'italy', 'es':'spain', 'nl':'netherlands', 
            'be':'belgium', 'at':'austria', 'pl':'poland', 'se':'sweden', 'dk':'denmark', 
            'fi':'finland', 'pt':'portugal', 'ie':'ireland', 'gr':'greece', 'cz':'czech republic', 
            'ro':'romania', 'hu':'hungary', 'bg':'bulgaria', 'sk':'slovakia', 'hr':'croatia', 
            'si':'slovenia', 'ee':'estonia', 'lv':'latvia', 'lt':'lithuania', 'cy':'cyprus', 
            'mt':'malta', 'lu':'luxembourg', 'ch':'switzerland', 'no':'norway', 
            'gb':'united kingdom', 'uk':'united kingdom', 'fra':'france', 'deu':'germany',
            'ita':'italy', 'esp':'spain', 'nld':'netherlands', 'gbr':'united kingdom'
        }
        if s in eu_map: return eu_map[s]
        for code, name in eu_map.items():
            if name in s: return name 
        return s
        
    elif reg == "🇺🇸 US":
        us_map = {
            'al':'alabama', 'ak':'alaska', 'az':'arizona', 'ar':'arkansas', 'ca':'california', 
            'co':'colorado', 'ct':'connecticut', 'de':'delaware', 'fl':'florida', 'ga':'georgia', 
            'hi':'hawaii', 'id':'idaho', 'il':'illinois', 'in':'indiana', 'ia':'iowa', 
            'ks':'kansas', 'ky':'kentucky', 'la':'louisiana', 'me':'maine', 'md':'maryland', 
            'ma':'massachusetts', 'mi':'michigan', 'mn':'minnesota', 'ms':'mississippi', 
            'mo':'missouri', 'mt':'montana', 'ne':'nebraska', 'nv':'nevada', 'nh':'new hampshire', 
            'nj':'new jersey', 'nm':'new mexico', 'ny':'new york', 'nc':'north carolina', 
            'nd':'north dakota', 'oh':'ohio', 'ok':'oklahoma', 'or':'oregon', 'pa':'pennsylvania', 
            'ri':'rhode island', 'sc':'south carolina', 'sd':'south dakota', 'tn':'tennessee', 
            'tx':'texas', 'ut':'utah', 'vt':'vermont', 'va':'virginia', 'wa':'washington', 
            'wv':'west virginia', 'wi':'wisconsin', 'wy':'wyoming'
        }
        return us_map.get(s, s)
        
    elif reg == "🇨🇦 CA":
        ca_map = {
            'ab':'alberta', 'bc':'british columbia', 'mb':'manitoba', 'nb':'new brunswick', 
            'nl':'newfoundland and labrador', 'ns':'nova scotia', 'nt':'northwest territories', 
            'nu':'nunavut', 'on':'ontario', 'pe':'prince edward island', 'qc':'quebec', 
            'sk':'saskatchewan', 'yt':'yukon'
        }
        return ca_map.get(s, s)
    return s

# --- REGEX STATE EXTRACTOR ---
def extract_state(val):
    if pd.isna(val): return ""
    v = str(val).upper().strip()
    if v == 'NAN' or v == '': return ""
    
    match = re.search(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b', v)
    if match: return match.group(1).lower()
    
    if ',' in v: 
        cleaned = v.split(',')[-1].strip()
        return cleaned.split()[0].lower() if cleaned else v.lower()
    return v.split()[-1].lower() if ' ' in v else v.lower()

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    noise = ["WORRY FREE", "DELIVERY", "PROTECTION", "NAN", "TOTAL", "HEALTH", "RISK", "ATTENTION", "SKU"]
    if any(x in s for x in noise) or s == "": return False
    return any(x in s for x in CAMS_PREFIX + ACCS_KEYWORDS)

def is_cam(s):
    s = str(s).upper().strip()
    if s in MP2_CAMS: return True
    if "PAPER" in s: return False
    if s.startswith("MP2-") and s not in MP2_CAMS: return False
    return any(s.startswith(x) for x in CAMS_PREFIX)

def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = range(df_po.shape[1])
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        
        region_map = {"🇺🇸 US": ["US"], "🇨🇦 CA": ["CA"], "🇬🇧 UK": ["UK"], "🇦🇺 AU": ["AU"], "🇪🇺 EU": ["EU", "GERMANY"]}
        keywords = region_map.get(region_label, [])
        is_amz = df_po[4].astype(str).str.contains("AMZ", case=False, na=False)
        
        if channel == "Amazon (FBA)": df_po = df_po[is_amz]
        else: df_po = df_po[~is_amz]
            
        pattern = '|'.join(keywords)
        df_po = df_po[df_po[4].astype(str).str.contains(pattern, case=False, na=False)]
        return df_po[[0, 5, 6, 9, 10]].rename(columns={0:'PO', 5:'SKU', 6:'Qty', 9:'ETA', 10:'Tracking'})
    except Exception as e: 
        return pd.DataFrame()

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance"]
if chan == "Shopify/WH":
    menu_options.append("🚚 3PL Costs & Logistics")
page = st.sidebar.radio("Dashboard View", menu_options)

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)
    
    df_po = get_filtered_po_data(chan, m_sel)
    po_sum = pd.DataFrame(columns=['SKU', 'Qty'])
    if not df_po.empty:
        st.subheader("🚚 Inbound Pipeline")
        st.dataframe(df_po, use_container_width=True, hide_index=True)
        po_sum = df_po.groupby('SKU')['Qty'].sum().reset_index()

    if m_sel in GIDS_FOR_MONTHS[chan]:
        st.subheader(f"🚨 3-Month Out-of-Stock Risk ({m_sel})")
        try:
            safety_full = load_csv(FORECAST_SHEET_ID, GID_SAFETY_SOURCE)
            r_start, r_end = REGION_RANGES[chan][m_sel]
            safety_df = safety_full.iloc[r_start:r_end].copy()
            safety_df.columns = [str(c).strip() for c in safety_df.columns]
            
            f_df = load_csv(FORECAST_SHEET_ID, GIDS_FOR_MONTHS[chan][m_sel])
            f_df.columns = [str(c).strip() for c in f_df.columns]
            
            target_dates = [(datetime.now().replace(day=1) + timedelta(days=31*i)).replace(day=1) for i in range(3)]
            target_ym = [(d.year, d.month) for d in target_dates]
            
            demand_cols = []
            for c in f_df.columns:
                try:
                    dt = pd.to_datetime(str(c).strip())
                    if (dt.year, dt.month) in target_ym: demand_cols.append(c)
                except: pass
            
            if not demand_cols:
                target_strs = [d.strftime('%Y-%m-01') for d in target_dates]
                demand_cols = [c for c in f_df.columns if str(c).strip() in target_strs]
            
            inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
            df_inv_risk = load_csv(MAIN_SHEET_ID, inv_gid)
            risk_inv = df_inv_risk.iloc[:, [0, m_map[m_sel]]].copy()
            risk_inv.columns = ["SKU", "Stock"]
            risk_inv["Stock"] = pd.to_numeric(risk_inv["Stock"], errors='coerce').fillna(0).astype(int)

            demand_dict = {}
            for _, row in f_df.iterrows():
                sku = str(row.iloc[0]).strip().upper()
                if not is_valid_sku(sku): continue
                row_demand = sum([pd.to_numeric(row[m], errors='coerce') for m in demand_cols])
                demand_dict[sku] = demand_dict.get(sku, 0) + row_demand

            risk_list = []
            for sku, demand in demand_dict.items():
                match_safe = safety_df[safety_df.iloc[:,0].astype(str).str.strip().str.upper() == sku]
                safe_val = pd.to_numeric(match_safe.iloc[:,2], errors='coerce').sum() if not match_safe.empty else 0
                
                live = risk_inv[risk_inv["SKU"].astype(str).str.strip().str.upper() == sku]["Stock"].sum()
                inbound = po_sum[po_sum["SKU"].astype(str).str.strip().str.upper() == sku]["Qty"].sum()
                
                balance = (live + inbound) - demand - safe_val
                
                if balance < 0 and live != 0:
                    risk_list.append({
                        "SKU": sku, "Stock": int(live), "Inbound": int(inbound), 
                        "3m Forecast": int(demand), "Shortage": int(abs(balance))
                    })
            
            if risk_list:
                st.error(f"⚠️ {len(risk_list)} SKUs at risk (excluding zero-stock items).")
                st.dataframe(pd.DataFrame(risk_list).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
            else: 
                st.success("✅ Forecast demand met.")
        except Exception as e: 
            st.warning(f"Risk calculation error: {e}")

    st.divider()
    df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    
    col_a, col_b = st.columns(2)
    with col_a: 
        st.subheader("📸 Cameras")
        st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with col_b: 
        st.subheader("🎒 Accessories")
        st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

# --- SALES PERFORMANCE ---
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
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        
        lt = df['date'].max()
        s_curr, e_curr = lt - timedelta(6), lt
        s_prev, e_prev = s_curr - timedelta(7), s_curr - timedelta(1)
        st.info(f"📍 **{reg}** | Weekly Window: {s_curr} to {e_curr}")
        
        curr_week = df[(df['date'] >= s_curr) & (df['date'] <= e_curr)].groupby('sku')['quantity'].sum().reset_index()
        prev_week = df[(df['date'] >= s_prev) & (df['date'] <= e_prev)].groupby('sku')['quantity'].sum().reset_index()
        recon = pd.merge(curr_week, prev_week, on='sku', how='outer', suffixes=('_C', '_P')).fillna(0)
        recon['Diff'] = recon['quantity_C'] - recon['quantity_P']
        
        m1, m2 = st.columns(2)
        with m1:
            v, o = recon[recon['sku'].apply(is_cam)]['quantity_C'].sum(), recon[recon['sku'].apply(is_cam)]['quantity_P'].sum()
            st.metric("📸 Camera Units", f"{int(v)}", delta=f"{int(v-o)}")
        with m2:
            v, o = recon[~recon['sku'].apply(is_cam)]['quantity_C'].sum(), recon[~recon['sku'].apply(is_cam)]['quantity_P'].sum()
            st.metric("🎒 Accessory Units", f"{int(v)}", delta=f"{int(v-o)}")

        st.divider()
        st.subheader("🚀 Weekly SKU Movers (Top 3 & Bottom 3)")
        cam_r, acc_r = recon[recon['sku'].apply(is_cam)], recon[~recon['sku'].apply(is_cam)]
        grid_a, grid_b = st.columns(2)
        with grid_a:
            st.success("📸 Camera Top 3")
            st.dataframe(cam_r[cam_r['Diff']>0].nlargest(3, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)
            st.error("📸 Camera Bottom 3")
            st.dataframe(cam_r[cam_r['Diff']<0].nsmallest(3, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)
        with grid_b:
            st.success("🎒 Accessory Top 3")
            st.dataframe(acc_r[acc_r['Diff']>0].nlargest(3, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)
            st.error("🎒 Accessory Bottom 3")
            st.dataframe(acc_r[acc_r['Diff']<0].nsmallest(3, 'Diff')[['sku', 'Diff']], hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top 5 SKU Rankings")
        ytd = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top 5 Cameras")
            top_c = ytd[ytd['sku'].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_c, hide_index=True, use_container_width=True)
        with y2:
            st.markdown("#### 🥇 Top 5 Accessories")
            top_a = ytd[~ytd['sku'].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_a, hide_index=True, use_container_width=True)

    except Exception as e: 
        st.error(f"Error: {e}")

# --- NEW ADDITION: 3PL COSTS & LOGISTICS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    
    reg_3pl = st.sidebar.selectbox("Select Region for 3PL Data", list(SUMMARY_COLS.keys()))
    has_shipping_data = reg_3pl in GIDS_3PL_SHIPPING
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    def clean_currency(val):
        if pd.isna(val): return 0.0
        v = str(val).replace('€', '').replace('$', '').replace('£', '').strip()
        if v == '': return 0.0
        if ',' in v and '.' in v:
            if v.rfind(',') > v.rfind('.'): v = v.replace('.', '').replace(',', '.')
            else: v = v.replace(',', '')
        elif ',' in v:
            parts = v.split(',')
            if len(parts) == 2 and len(parts[1]) in [1, 2]: v = v.replace(',', '.')
            else: v = v.replace(',', '')
        v = ''.join(c for c in v if c.isdigit() or c in '.-')
        if v in ['', '-', '.']: return 0.0
        return float(v)

    if has_shipping_data:
        t_sum, t_ship = st.tabs(["📊 Cost Summary", "🗺️ Shipping Analysis"])
    else:
        t_sum = st.container()
        st.info(f"ℹ️ {reg_3pl} only contains Summary data.")

    # ==========================================
    # TAB 1: SUMMARY COSTS 
    # ==========================================
    with t_sum:
        try:
            df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY)
            df_sum.columns = range(df_sum.shape[1])
            df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
            df_sum = df_sum.dropna(subset=[0]) 
            
            cols = SUMMARY_COLS[reg_3pl]
            f_col, s_col, st_col = cols["fulfill"], cols["shipping"], cols["storage"]
            
            for c in [f_col, s_col, st_col]:
                if c < df_sum.shape[1]: df_sum[c] = df_sum[c].apply(clean_currency)
            
            df_sum['YM'] = df_sum[0].dt.to_period('M')
            valid_cols = [c for c in [f_col, s_col, st_col] if c < df_sum.shape[1]]
            monthly_costs = df_sum.groupby('YM')[valid_cols].sum().sum(axis=1)
            valid_months = monthly_costs[monthly_costs > 0]
            
            global_curr_m = datetime.now().month
            
            if valid_months.empty:
                st.warning("⚠️ Could not find any costs greater than 0 in the data.")
            else:
                most_recent_ym = valid_months.index.max()
                curr_m, curr_y = most_recent_ym.month, most_recent_ym.year
                global_curr_m = curr_m 
                
                prev_m, prev_y = (12, curr_y - 1) if curr_m == 1 else (curr_m - 1, curr_y)
                    
                df_curr = df_sum[(df_sum[0].dt.month == curr_m) & (df_sum[0].dt.year == curr_y)]
                df_prev = df_sum[(df_sum[0].dt.month == prev_m) & (df_sum[0].dt.year == prev_y)]
                
                display_date_str = datetime(curr_y, curr_m, 1).strftime('%B %Y')
                st.subheader(f"💸 Monthly Cost Overview ({display_date_str})")
                
                curr_fulfill = df_curr[f_col].sum() if f_col < df_curr.shape[1] else 0
                prev_fulfill = df_prev[f_col].sum() if f_col < df_prev.shape[1] else 0
                
                curr_shipping = df_curr[s_col].sum() if s_col < df_curr.shape[1] else 0
                prev_shipping = df_prev[s_col].sum() if s_col < df_prev.shape[1] else 0
                
                curr_storage = df_curr[st_col].sum() if st_col < df_curr.shape[1] else 0
                prev_storage = df_prev[st_col].sum() if st_col < df_curr.shape[1] else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Storage Cost", f"{cur}{curr_storage:,.2f}", delta=f"{cur}{curr_storage - prev_storage:,.2f}", delta_color="inverse")
                c2.metric("Fulfillment Cost", f"{cur}{curr_fulfill:,.2f}", delta=f"{cur}{curr_fulfill - prev_fulfill:,.2f}", delta_color="inverse")
                c3.metric("Total Shipping Cost", f"{cur}{curr_shipping:,.2f}", delta=f"{cur}{curr_shipping - prev_shipping:,.2f}", delta_color="inverse")

                st.divider()
                st.subheader("📋 Monthly Cost Breakdown")
                
                trend_df = df_sum[[0, f_col, s_col, st_col]].copy()
                trend_df = trend_df.rename(columns={0: 'Date', f_col: 'Fulfillment Cost', s_
