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

GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}
GID_3PL_SUMMARY = "972554877" 
GID_PO_GRID = "1801670245"
GIDS_3PL_SHIPPING = {"🇺🇸 US": "1369957058", "🇨🇦 CA": "332821648", "🇪🇺 EU": "1032280204"}
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
    # FIXED: Handled empty strings explicitly so they don't break the 'in' function
    if not s or s == "NAN": return False
    
    noise = ["TOTAL", "HEALTH", "RISK", "SHIPPING", "PROTECTION"]
    if any(x in s for x in noise): return False
    
    valid_prefixes = ["MA-","MC-","MK-","MP-","MV-","MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"]
    return any(x in s for x in valid_prefixes)

def is_cam(s):
    s = str(s).upper().strip()
    if s in ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]: return True
    return any(s.startswith(x) for x in ["MA-","MC-","MK-","MP-","MV-"])

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Sales Channel", ["Shopify/WH", "Amazon (FBA)"])
menu_options = ["📦 Inventory & Risk", "💰 Sales Performance", "🚚 3PL Costs & Logistics"]
page = st.sidebar.radio("Dashboard View", menu_options)

# ==========================================
# 1. INVENTORY & RISK
# ==========================================
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)

    # 1A. Inbound Pipeline
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
    except Exception as e: st.warning(f"Could not load Inbound data: {e}")

    # 1B. Stock Levels (OOS, Low, Full)
    inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
    df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1: 
        st.subheader("🔴 Out of Stock (OOS)")
        oos_items = s_df[s_df["Stock"]==0]
        if not oos_items.empty: st.dataframe(oos_items, hide_index=True)
        else: st.success("✅ Fully Stocked")
    with c2: 
        st.subheader("🟡 Low Stock (<50)")
        low_items = s_df[(s_df["Stock"]>0)&(s_df["Stock"]<50)].sort_values(by="Stock")
        if not low_items.empty: st.dataframe(low_items, hide_index=True)
        else: st.success("✅ All items > 50 units")
    
    st.divider()
    st.subheader("📋 Full Inventory List")
    col_a, col_b = st.columns(2)
    with col_a: st.markdown("#### 📸 Cameras"); st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with col_b: st.markdown("#### 🎒 Accessories"); st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

# ==========================================
# 2. SALES PERFORMANCE
# ==========================================
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
        
        # Clean Data
        df['clean_date'] = pd.to_datetime(df[d_col], errors='coerce').dt.date
        df = df[df[s_col].apply(is_valid_sku)]
        df['quantity'] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        
        # Strict Date Window
        target_start, target_end = datetime(2026, 4, 27).date(), datetime(2026, 5, 3).date()
        prev_start, prev_end = target_start - timedelta(7), target_start - timedelta(1)
        st.info(f"📍 **Confirmed Audit Window:** April 27 to May 3")
        
        curr_w = df[(df['clean_date'] >= target_start) & (df['clean_date'] <= target_end)]
        prev_w = df[(df['clean_date'] >= prev_start) & (df['clean_date'] <= prev_end)]
        
        # Bulletproof Merge
        c_sum = curr_w.groupby(s_col)['quantity'].sum().reset_index()
        p_sum = prev_w.groupby(s_col)['quantity'].sum().reset_index()
        
        if c_sum.empty and p_sum.empty:
            st.warning("⚠️ No sales recorded for this period.")
        else:
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
            st.subheader("🚀 Weekly SKU Rankings")
            c1, c2 = st.columns(2)
            with c1: 
                st.success("📈 Top 5 Weekly Sellers")
                st.dataframe(recon.nlargest(5, 'quantity_C')[[s_col, 'quantity_C']].rename(columns={s_col:'SKU', 'quantity_C':'Units'}), hide_index=True, use_container_width=True)
            with c2: 
                st.error("📉 Bottom 5 Weekly Sellers")
                bottom_week = recon[recon['quantity_C'] > 0]
                st.dataframe(bottom_week.nsmallest(5, 'quantity_C')[[s_col, 'quantity_C']].rename(columns={s_col:'SKU', 'quantity_C':'Units'}), hide_index=True, use_container_width=True)

        # YTD Section
        st.divider()
        st.subheader(f"🏆 YTD {target_end.year} Rankings")
        ytd = df[pd.to_datetime(df['clean_date']).dt.year == target_end.year].groupby(s_col)['quantity'].sum().reset_index()
        
        if not ytd.empty:
            ytd = ytd[ytd['quantity'] > 0] # Clean 0s
            y1, y2 = st.columns(2)
            with y1: 
                st.markdown("#### 🥇 Top 5 Sellers (YTD)")
                st.dataframe(ytd.nlargest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Units'}), hide_index=True, use_container_width=True)
            with y2: 
                st.markdown("#### 📉 Bottom 5 Sellers (YTD)")
                st.dataframe(ytd.nsmallest(5, 'quantity').rename(columns={s_col:'SKU','quantity':'Units'}), hide_index=True, use_container_width=True)
                
    except Exception as e: st.error(f"Error loading sales data: {e}")

# ==========================================
# 3. 3PL COSTS & LOGISTICS
# ==========================================
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    reg_3pl = st.sidebar.selectbox("Region", list(SUMMARY_COLS.keys()))
    cur = "€" if reg_3pl == "🇪🇺 EU" else "$"
    
    t_sum, t_ship = st.tabs(["📊 Cost Summary", "🗺️ Shipping Region Analysis"])
    
    # 3A. COST SUMMARY
    with t_sum:
        try:
            df_sum = load_csv(THREE_PL_SHEET_ID, GID_3PL_SUMMARY)
            df_sum.columns = range(df_sum.shape[1])
            df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
            df_sum = df_sum.dropna(subset=[0])
            
            cols = SUMMARY_COLS[reg_3pl]
            for c in [cols["fulfill"], cols["shipping"], cols["storage"]]:
                df_sum[c] = pd.to_numeric(df_sum[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
            
            monthly = df_sum.groupby(df_sum[0].dt.to_period('M'))[[cols["fulfill"], cols["shipping"], cols["storage"]]].sum()
            latest_month = monthly.index[-1]
            latest = monthly.iloc[-1]
            
            st.subheader(f"💸 Monthly Overview ({latest_month.strftime('%B %Y')})")
            c1, c2, c3 = st.columns(3)
            c1.metric("Storage Cost", f"{cur}{latest[cols['storage']]:,.2f}")
            c2.metric("Warehouse Fulfillment Cost", f"{cur}{latest[cols['fulfill']]:,.2f}")
            c3.metric("Shipping Cost", f"{cur}{latest[cols['shipping']]:,.2f}")
            
            st.divider()
            st.subheader("📋 Historical Cost Breakdown")
            trend = monthly.iloc[::-1].copy().reset_index()
            trend.columns = ['Month', 'Fulfillment', 'Shipping', 'Storage']
            trend['Month'] = trend['Month'].astype(str)
            st.dataframe(trend.style.format({c:f'{cur}{{:.2f}}' for c in ['Fulfillment','Shipping','Storage']}), hide_index=True, use_container_width=True)
            
        except Exception as e: st.error(f"Summary cost data unavailable: {e}")

    # 3B. SHIPPING ANALYSIS
    with t_ship:
        try:
            # Load Raw Orders
            raw = load_csv(THREE_PL_SHEET_ID, GIDS_RAW_SHIPPING[reg_3pl])
            raw.columns = range(raw.shape[1])
            
            # Find date column and filter for latest month to match summary
            best_date_col = next((c for c in range(15) if pd.to_datetime(raw[c], errors='coerce').notna().sum() > 5), 0)
            raw['ParsedDate'] = pd.to_datetime(raw[best_date_col], errors='coerce')
            raw_valid = raw.dropna(subset=['ParsedDate']).copy()
            curr_y = raw_valid['ParsedDate'].dt.year.max()
            curr_m = raw_valid[raw_valid['ParsedDate'].dt.year == curr_y]['ParsedDate'].dt.month.max()
            
            raw_recent = raw_valid[(raw_valid['ParsedDate'].dt.year == curr_y) & (raw_valid['ParsedDate'].dt.month == curr_m)].copy()
            order_col = 12 if reg_3pl == "🇪🇺 EU" else 2
            
            # Load Costs by Location
            df_states_raw = load_csv(THREE_PL_SHEET_ID, GIDS_3PL_SHIPPING[reg_3pl])
            df_states_raw.columns = range(df_states_raw.shape[1])
            df_slice = df_states_raw.iloc[1:].copy()
            month_col_idx = curr_m # Assuming columns match month numbers
            
            # Clean Cost column
            df_slice[month_col_idx] = pd.to_numeric(df_slice[month_col_idx].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
            df_filtered = df_slice[[0, month_col_idx]].rename(columns={0: "Location", month_col_idx: "Shipping Cost"})
            df_filtered = df_filtered[(df_filtered["Shipping Cost"] > 0) & (~df_filtered["Location"].astype(str).str.lower().str.contains("total"))].copy()
            df_filtered["Match_Loc"] = df_filtered["Location"].apply(lambda x: normalize_loc(x, reg_3pl))

            # Display Metrics
            total_orders = raw_recent[order_col].nunique()
            st.markdown(f"#### 📊 Order Metrics ({datetime(curr_y, curr_m, 1).strftime('%B %Y')})")
            st.metric("Orders Shipped", f"{total_orders:,}")
            
            if reg_3pl in ["🇺🇸 US", "🇨🇦 CA"]:
                st.divider()
                st.markdown("#### 🗺️ Regional Distribution")
                raw_recent['State'] = raw_recent[4].apply(extract_state)
                raw_recent['Macro'] = raw_recent['State'].map(US_MACRO if reg_3pl=="🇺🇸 US" else CA_MACRO).fillna('Other')
                dist = raw_recent.groupby('Macro')[order_col].nunique().reset_index().rename(columns={order_col:'Orders'})
                
                c1, c2 = st.columns(2)
                with c1: st.altair_chart(alt.Chart(dist).mark_arc(innerRadius=50).encode(theta='Orders', color='Macro'), use_container_width=True)
                with c2: 
                    dist['%'] = (dist['Orders'] / dist['Orders'].sum()) * 100
                    dist['Percentage'] = dist['%'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(dist[['Macro', 'Orders', 'Percentage']].sort_values(by='Orders', ascending=False), hide_index=True)
                
                st.divider()
                st.markdown(f"#### 📍 Cost & Orders by Location")
                raw_recent['Match_Loc'] = raw_recent[4].apply(extract_state).apply(lambda x: normalize_loc(x, reg_3pl))
                loc_counts = raw_recent[raw_recent['Match_Loc'] != ""].groupby('Match_Loc')[order_col].nunique().reset_index().rename(columns={order_col:'Orders'})
                df_final = pd.merge(df_filtered, loc_counts, on='Match_Loc', how='left').fillna(0)
                df_display = df_final[['Location', 'Orders', 'Shipping Cost']].sort_values(by="Shipping Cost", ascending=False).copy()
                df_display['Shipping Cost'] = df_display['Shipping Cost'].apply(lambda x: f"{cur}{x:,.2f}")
                st.dataframe(df_display, hide_index=True, use_container_width=True)
                
                st.divider()
                st.markdown(f"#### 🏆 YTD Top 3 Destinations")
                raw_ytd = raw_valid[raw_valid['ParsedDate'].dt.year == curr_y].copy()
                raw_ytd['Match_Loc'] = raw_ytd[4].apply(extract_state).apply(lambda x: normalize_loc(x, reg_3pl))
                ytd_counts = raw_ytd[raw_ytd['Match_Loc'] != ""].groupby('Match_Loc')[order_col].nunique().reset_index()
                if not ytd_counts.empty:
                    ytd_counts['%'] = (ytd_counts[order_col] / ytd_counts[order_col].sum()) * 100
                    top3 = ytd_counts.nlargest(3, order_col).copy()
                    top3['Location'] = top3['Match_Loc'].str.title()
                    top3['Percentage'] = top3['%'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(top3[['Location', 'Percentage']], hide_index=True, use_container_width=True)

            else:
                # EU specific logic
                st.divider()
                st.markdown(f"#### 📍 Cost & Orders by Country")
                raw_recent['Match_Loc'] = raw_recent[14].apply(lambda x: normalize_loc(x, reg_3pl))
                loc_counts = raw_recent[raw_recent['Match_Loc'] != ""].groupby('Match_Loc')[order_col].nunique().reset_index().rename(columns={order_col:'Orders'})
                df_final = pd.merge(df_filtered, loc_counts, on='Match_Loc', how='left').fillna(0)
                df_display = df_final[['Location', 'Orders', 'Shipping Cost']].sort_values(by="Shipping Cost", ascending=False).copy()
                df_display['Shipping Cost'] = df_display['Shipping Cost'].apply(lambda x: f"{cur}{x:,.2f}")
                st.dataframe(df_display, hide_index=True, use_container_width=True)

        except Exception as e: st.error(f"Shipping analysis error: {e}")

# --- END OF FILE ---
