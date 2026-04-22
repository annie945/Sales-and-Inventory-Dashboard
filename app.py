import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

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

# Column mappings (0-indexed: A=0, B=1, C=2...)
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
    "🇨🇦 CA": "91803080" 
}

# --- REGION RANGES FOR SAFETY STOCK ---
REGION_RANGES = {
    "Shopify/WH": {"🇺🇸 US": (1, 21), "🇨🇦 CA": (22, 42), "🇬🇧 UK": (44, 64), "🇪🇺 EU": (66, 86), "🇦🇺 AU": (88, 108)},
    "Amazon (FBA)": {"🇺🇸 US": (110, 130), "🇨🇦 CA": (131, 151)}
}

# --- CATEGORY LOGIC ---
CAMS_PREFIX = ["MA-","MC-","MK-","MP-","MV-"]
MP2_CAMS = ["MP2-BLUE", "MP2-MINT", "MP2-SP", "MP2-WP"]
ACCS_KEYWORDS = ["MICROSD","TML-","BAG-","LANYARD", "PAPER", "MP2-"]

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    noise = ["WORRY FREE", "DELIVERY", "PROTECTION", "NAN", "TOTAL", "HEALTH", "RISK", "ATTENTION", "SKU"]
    if any(x in s for x in noise) or s == "": 
        return False
    return any(x in s for x in CAMS_PREFIX + ACCS_KEYWORDS)

def is_cam(s):
    s = str(s).upper().strip()
    if s in MP2_CAMS: 
        return True
    if "PAPER" in s: 
        return False
    if s.startswith("MP2-") and s not in MP2_CAMS: 
        return False
    return any(s.startswith(x) for x in CAMS_PREFIX)

def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = range(df_po.shape[1])
        
        not_received = df_po[11].astype(str).str.upper() != "RECEIVED"
        df_po = df_po[not_received]
        
        region_map = {"🇺🇸 US": ["US"], "🇨🇦 CA": ["CA"], "🇬🇧 UK": ["UK"], "🇦🇺 AU": ["AU"], "🇪🇺 EU": ["EU", "GERMANY"]}
        keywords = region_map.get(region_label, [])
        
        is_amz = df_po[4].astype(str).str.contains("AMZ", case=False, na=False)
        
        if channel == "Amazon (FBA)":
            df_po = df_po[is_amz]
        else:
            df_po = df_po[~is_amz]
            
        pattern = '|'.join(keywords)
        has_region = df_po[4].astype(str).str.contains(pattern, case=False, na=False)
        df_po = df_po[has_region]
        
        cols_to_keep = [0, 5, 6, 9, 10]
        df_po = df_po[cols_to_keep]
        
        rename_dict = {0:'PO', 5:'SKU', 6:'Qty', 9:'ETA', 10:'Tracking'}
        return df_po.rename(columns=rename_dict)
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
    
    if chan == "Amazon (FBA)":
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18}
    else:
        m_map = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        
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
            
            target_months = []
            for i in range(3):
                date_val = (datetime.now().replace(day=1) + timedelta(days=31*i))
                date_val = date_val.replace(day=1)
                target_months.append(date_val.strftime('%Y-%m-01'))
            
            inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
            df_inv_risk = load_csv(MAIN_SHEET_ID, inv_gid)
            
            inv_col_idx = m_map[m_sel]
            risk_inv = df_inv_risk.iloc[:, [0, inv_col_idx]].copy()
            risk_inv.columns = ["SKU", "Stock"]
            
            risk_inv["Stock"] = pd.to_numeric(
                risk_inv["Stock"], errors='coerce'
            ).fillna(0).astype(int)

            risk_list = []
            for _, row in f_df.iterrows():
                sku = str(row.iloc[0]).strip()
                if not is_valid_sku(sku): 
                    continue
                
                demand = 0
                for m in target_months:
                    if m in f_df.columns:
                        val = pd.to_numeric(row[m], errors='coerce')
                        if pd.notna(val):
                            demand += val
                
                safe_skus = safety_df.iloc[:,0].astype(str).str.lower().str.strip()
                match_safe = safety_df[safe_skus == sku.lower()]
                safe_val = 0
                if not match_safe.empty:
                    safe_val = pd.to_numeric(match_safe.iloc[0,2], errors='coerce')
                    if pd.isna(safe_val): safe_val = 0
                
                live_skus = risk_inv["SKU"].astype(str).str.lower().str.strip()
                match_live = risk_inv[live_skus == sku.lower()]
                live = match_live["Stock"].sum()
                
                inbound_skus = po_sum["SKU"].astype(str).str.lower().str.strip()
                match_inbound = po_sum[inbound_skus == sku.lower()]
                inbound = match_inbound["Qty"].sum()
                
                balance = (live + inbound) - demand - safe_val
                if balance < 0:
                    risk_list.append({
                        "SKU": sku.upper(), 
                        "Stock": int(live), 
                        "Inbound": int(inbound), 
                        "3m Forecast": int(demand), 
                        "Shortage": int(abs(balance))
                    })
            
            if risk_list:
                st.error(f"⚠️ {len(risk_list)} SKUs at risk.")
                df_risk_display = pd.DataFrame(risk_list)
                df_risk_display = df_risk_display.sort_values(by="Shortage", ascending=False)
                st.dataframe(df_risk_display, use_container_width=True, hide_index=True)
            else: 
                st.success("✅ Forecast demand met.")
        except Exception as e: 
            st.warning(f"Risk calculation error: {e}")

    st.divider()
    
    inv_gid_2 = "856174189" if chan == "Amazon (FBA)" else "0"
    df_inv = load_csv(MAIN_SHEET_ID, inv_gid_2)
    
    inv_col_index = m_map[m_sel]
    s_df = df_inv.iloc[:, [0, inv_col_index]].copy()
    s_df.columns = ["SKU", "Stock"]
    
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    
    s_df["Stock"] = pd.to_numeric(
        s_df["Stock"], errors='coerce'
    ).fillna(0).astype(int)
    
    col_a, col_b = st.columns(2)
    with col_a: 
        st.subheader("📸 Cameras")
        cam_df = s_df[s_df["SKU"].apply(is_cam)]
        st.dataframe(cam_df, hide_index=True, use_container_width=True)
    with col_b: 
        st.subheader("🎒 Accessories")
        acc_df = s_df[~s_df["SKU"].apply(is_cam)]
        st.dataframe(acc_df, hide_index=True, use_container_width=True)

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
        
        df['quantity'] = pd.to_numeric(
            df['quantity'], errors='coerce'
        ).fillna(0)
        
        lt = df['date'].max()
        s_curr = lt - timedelta(6)
        e_curr = lt
        s_prev = s_curr - timedelta(7)
        e_prev = s_curr - timedelta(1)
        
        st.info(f"📍 **{reg}** | Weekly Window: {s_curr} to {e_curr}")
        
        mask_curr = (df['date'] >= s_curr) & (df['date'] <= e_curr)
        curr_week = df[mask_curr].groupby('sku')['quantity'].sum().reset_index()
        
        mask_prev = (df['date'] >= s_prev) & (df['date'] <= e_prev)
        prev_week = df[mask_prev].groupby('sku')['quantity'].sum().reset_index()
        
        recon = pd.merge(curr_week, prev_week, on='sku', how='outer', suffixes=('_C', '_P'))
        recon = recon.fillna(0)
        recon['Diff'] = recon['quantity_C'] - recon['quantity_P']
        recon = recon[recon['quantity_C'] > 0]
        
        m1, m2 = st.columns(2)
        with m1:
            cam_mask = recon['sku'].apply(is_cam)
            v = recon[cam_mask]['quantity_C'].sum()
            o = recon[cam_mask]['quantity_P'].sum()
            st.metric("📸 Camera Units", f"{int(v)}", delta=f"{int(v-o)}")
        with m2:
            acc_mask = ~recon['sku'].apply(is_cam)
            v = recon[acc_mask]['quantity_C'].sum()
            o = recon[acc_mask]['quantity_P'].sum()
            st.metric("🎒 Accessory Units", f"{int(v)}", delta=f"{int(v-o)}")

        st.divider()
        st.subheader("🚀 Weekly SKU Movers (Top 3 & Bottom 3)")
        cam_r = recon[recon['sku'].apply(is_cam)]
        acc_r = recon[~recon['sku'].apply(is_cam)]
        
        grid_a, grid_b = st.columns(2)
        with grid_a:
            st.success("📸 Camera Top 3")
            top_cam = cam_r[cam_r['Diff']>0].nlargest(3, 'Diff')[['sku', 'Diff']]
            st.dataframe(top_cam, hide_index=True, use_container_width=True)
            
            st.error("📸 Camera Bottom 3")
            bot_cam = cam_r[cam_r['Diff']<0].nsmallest(3, 'Diff')[['sku', 'Diff']]
            st.dataframe(bot_cam, hide_index=True, use_container_width=True)
            
        with grid_b:
            st.success("🎒 Accessory Top 3")
            top_acc = acc_r[acc_r['Diff']>0].nlargest(3, 'Diff')[['sku', 'Diff']]
            st.dataframe(top_acc, hide_index=True, use_container_width=True)
            
            st.error("🎒 Accessory Bottom 3")
            bot_acc = acc_r[acc_r['Diff']<0].nsmallest(3, 'Diff')[['sku', 'Diff']]
            st.dataframe(bot_acc, hide_index=True, use_container_width=True)

        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top 5 SKU Rankings")
        ytd_mask = pd.to_datetime(df['date']).dt.year == lt.year
        ytd = df[ytd_mask].groupby('sku')['quantity'].sum().reset_index()
        y1, y2 = st.columns(2)
        with y1:
            st.markdown("#### 🥇 Top 5 Cameras")
            top_c = ytd[ytd['sku'].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_c, hide_index=True, use_container_width=True)
            st.write(f"**Total Units:** {int(top_c['quantity'].sum()):,}")
        with y2:
            st.markdown("#### 🥇 Top 5 Accessories")
            top_a = ytd[~ytd['sku'].apply(is_cam)].nlargest(5, 'quantity')
            st.dataframe(top_a, hide_index=True, use_container_width=True)
            st.write(f"**Total Units:** {int(top_a['quantity'].sum()):,}")

    except Exception as e: 
        st.error(f"Error: {e}")

# --- NEW ADDITION: 3PL COSTS & LOGISTICS ---
elif page == "🚚 3PL Costs & Logistics":
    st.title("🚚 3PL Costs & Logistics Analytics")
    
    reg_3pl = st.sidebar.selectbox("Select Region for 3PL Data", list(SUMMARY_COLS.keys()))
    has_shipping_data = reg_3pl in GIDS_3PL_SHIPPING
    
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
            
            num_cols = df_sum.shape[1]
            df_sum.columns = range(num_cols)
            
            df_sum[0] = pd.to_datetime(df_sum[0], errors='coerce')
            df_sum = df_sum.dropna(subset=[0]) 
            
            cols = SUMMARY_COLS[reg_3pl]
            f_col = cols["fulfill"]
            s_col = cols["shipping"]
            st_col = cols["storage"]
            
            for c in [f_col, s_col, st_col]:
                if c < df_sum.shape[1]: 
                    clean_str = df_sum[c].astype(str).str.replace(r'[$, ]', '', regex=True)
                    df_sum[c] = pd.to_numeric(clean_str, errors='coerce').fillna(0)
            
            df_sum['YM'] = df_sum[0].dt.to_period('M')
            
            valid_cols = []
            for c in [f_col, s_col, st_col]:
                if c < df_sum.shape[1]:
                    valid_cols.append(c)
                    
            monthly_costs = df_sum.groupby('YM')[valid_cols].sum().sum(axis=1)
            valid_months = monthly_costs[monthly_costs > 0]
            
            if valid_months.empty:
                st.warning("⚠️ Could not find any costs greater than $0 in the data.")
            else:
                most_recent_ym = valid_months.index.max()
                curr_m = most_recent_ym.month
                curr_y = most_recent_ym.year
                
                if curr_m == 1:
                    prev_m = 12
                    prev_y = curr_y - 1
                else:
                    prev_m = curr_m - 1
                    prev_y = curr_y
                    
                curr_mask = (df_sum[0].dt.month == curr_m) & (df_sum[0].dt.year == curr_y)
                df_curr = df_sum[curr_mask]
                
                prev_mask = (df_sum[0].dt.month == prev_m) & (df_sum[0].dt.year == prev_y)
                df_prev = df_sum[prev_mask]
                
                display_date_str = datetime(curr_y, curr_m, 1).strftime('%B %Y')
                st.subheader(f"💸 Monthly Cost Overview ({display_date_str})")
                
                curr_fulfill = df_curr[f_col].sum() if f_col < df_curr.shape[1] else 0
                prev_fulfill = df_prev[f_col].sum() if f_col < df_prev.shape[1] else 0
                
                curr_shipping = df_curr[s_col].sum() if s_col < df_curr.shape[1] else 0
                prev_shipping = df_prev[s_col].sum() if s_col < df_prev.shape[1] else 0
                
                curr_storage = df_curr[st_col].sum() if st_col < df_curr.shape[1] else 0
                prev_storage = df_prev[st_col].sum() if st_col < df_prev.shape[1] else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Storage Cost", 
                    f"${curr_storage:,.2f}", 
                    delta=f"${curr_storage - prev_storage:,.2f}", 
                    delta_color="inverse"
                )
                c2.metric(
                    "Fulfillment Cost", 
                    f"${curr_fulfill:,.2f}", 
                    delta=f"${curr_fulfill - prev_fulfill:,.2f}", 
                    delta_color="inverse"
                )
                c3.metric(
                    "Total Shipping Cost", 
                    f"${curr_shipping:,.2f}", 
                    delta=f"${curr_shipping - prev_shipping:,.2f}", 
                    delta_color="inverse"
                )

                st.divider()
                st.subheader("📋 Monthly Cost Breakdown")
                
                trend_df = df_sum[[0, f_col, s_col, st_col]].copy()
                trend_df = trend_df.rename(columns={
                    0: 'Date',
                    f_col: 'Fulfillment Cost',
                    s_col: 'Shipping Cost',
                    st_col: 'Storage Cost'
                })
                
                trend_df['MonthPeriod'] = trend_df['Date'].dt.to_period('M')
                
                group_cols = ['Fulfillment Cost', 'Shipping Cost', 'Storage Cost']
                monthly_trend = trend_df.groupby('MonthPeriod')[group_cols].sum()
                
                monthly_trend = monthly_trend[(monthly_trend.T != 0).any()]
                
                table_display = monthly_trend.copy()
                table_display.index = table_display.index.astype(str) 
                table_display['Total Monthly Cost'] = table_display.sum(axis=1)
                
                table_display = table_display.iloc[::-1]
                
                for col in table_display.columns:
                    table_display[col] = table_display[col].map("${:,.2f}".format)
                
                table_display.index.name = "Month"
                
                st.dataframe(table_display, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error loading Summary data: {e}")

    # ==========================================
    # TAB 2: SHIPPING ANALYSIS 
    # ==========================================
    if has_shipping_data:
        with t_ship:
            try:
                st.subheader(f"🗺️ {reg_3pl} Shipping Analysis")
                
                # --- SECTION 1: RAW DATA (CARRIERS & ORDER SIZES) ---
                raw_gid = GIDS_RAW_SHIPPING.get(reg_3pl, "")
                if raw_gid:
                    df_raw = load_csv(THREE_PL_SHEET_ID, raw_gid)
                    df_raw.columns = range(df_raw.shape[1])
                    
                    if df_raw.shape[1] >= 12: 
                        # Find the date column (usually column 0 or 1 in raw exports)
                        df_raw['ParsedDate'] = pd.to_datetime(df_raw[0], errors='coerce')
                        if df_raw['ParsedDate'].isna().all():
                            df_raw['ParsedDate'] = pd.to_datetime(df_raw[1], errors='coerce')

                        df_raw_valid = df_raw.dropna(subset=['ParsedDate']).copy()
                        
                        if not df_raw_valid.empty:
                            # Find Most Recent Month dynamically
                            recent_date = df_raw_valid['ParsedDate'].max()
                            curr_m = recent_date.month
                            curr_y = recent_date.year
                            
                            # Calculate Previous Month
                            if curr_m == 1:
                                prev_m = 12
                                prev_y = curr_y - 1
                            else:
                                prev_m = curr_m - 1
                                prev_y = curr_y
                            
                            # Filter to current and previous months
                            mask_recent = (df_raw_valid['ParsedDate'].dt.month == curr_m) & (df_raw_valid['ParsedDate'].dt.year == curr_y)
                            df_raw_recent = df_raw_valid[mask_recent]
                            
                            mask_prev = (df_raw_valid['ParsedDate'].dt.month == prev_m) & (df_raw_valid['ParsedDate'].dt.year == prev_y)
                            df_raw_prev = df_raw_valid[mask_prev]
                            
                            # Col C (2) = Order Count, Col L (11) = Avg Size (Current Month)
                            total_orders = df_raw_recent[2].replace('', pd.NA).dropna().count()
                            avg_order_size = pd.to_numeric(df_raw_recent[11], errors='coerce').mean()
                            
                            # Previous Month calculations for Delta
                            prev_total_orders = df_raw_prev[2].replace('', pd.NA).dropna().count()
                            prev_avg_order_size = pd.to_numeric(df_raw_prev[11], errors='coerce').mean()
                            
                            # Handle empty previous months gracefully
                            prev_total_orders = 0 if pd.isna(prev_total_orders) else prev_total_orders
                            prev_avg_order_size = 0 if pd.isna(prev_avg_order_size) else prev_avg_order_size
                            avg_order_size = 0 if pd.isna(avg_order_size) else avg_order_size
                            
                            delta_orders = int(total_orders - prev_total_orders)
                            delta_size = float(avg_order_size - prev_avg_order_size)
                            
                            display_month_str = recent_date.strftime('%B %Y')
                            st.markdown(f"#### 📊 Order Metrics ({display_month_str})")
                            
                            col1, col2 = st.columns(2)
                            col1.metric("📦 Orders Shipped", f"{int(total_orders):,}", delta=delta_orders)
                            col2.metric("📏 Average Order Size", f"{avg_order_size:,.2f}", delta=f"{delta_size:,.2f}")
                            
                            st.divider()
                            st.markdown(f"#### 🚚 Carrier Usage Percentage ({display_month_str})")
                            
                            # Col G (6) = Carrier Name
                            carriers = df_raw_recent[6].replace('', pd.NA).dropna()
                            if not carriers.empty:
                                c_counts = carriers.value_counts().reset_index()
                                c_counts.columns = ['Carrier', 'Orders']
                                c_counts['Percentage'] = (c_counts['Orders'] / c_counts['Orders'].sum()) * 100
                                
                                chart_col, table_col = st.columns([1, 1])
                                
                                with chart_col:
                                    # BEAUTIFUL NATIVE PIE CHART
                                    pie = alt.Chart(c_counts).mark_arc(innerRadius=50).encode(
                                        theta=alt.Theta(field="Orders", type="quantitative"),
                                        color=alt.Color(field="Carrier", type="nominal"),
                                        tooltip=['Carrier', 'Orders', alt.Tooltip('Percentage', format='.1f')]
                                    ).properties(height=350)
                                    st.altair_chart(pie, use_container_width=True)
                                
                                with table_col:
                                    disp_counts = c_counts.copy()
                                    disp_counts['Percentage'] = disp_counts['Percentage'].map("{:.1f}%".format)
                                    st.dataframe(disp_counts, hide_index=True, use_container_width=True)
                        else:
                            st.info("⚠️ Could not find dates in raw data to filter by month.")
                else:
                    st.info(f"ℹ️ Raw shipping data GID not yet mapped for {reg_3pl}. Order & Carrier metrics skipped.")

                st.divider()

                # --- SECTION 2: STATES & PROVINCES SUMMARY ---
                st.markdown(f"#### 📍 {reg_3pl} Cost by State/Province")
                df_states_raw = load_csv(THREE_PL_SHEET_ID, GIDS_3PL_SHIPPING[reg_3pl])
                df_states_raw.columns = range(df_states_raw.shape[1])
                
                # Slicing ranges based exactly on the Google Sheet structure
                if reg_3pl == "🇺🇸 US":
                    # Row A2 to A51 = index 0 to 49 in pandas
                    df_slice = df_states_raw.iloc[0:50].copy()
                elif reg_3pl == "🇨🇦 CA":
                    # Row A2 to A14 = index 0 to 12
                    df_slice = df_states_raw.iloc[0:13].copy()
                else:
                    df_slice = df_states_raw.copy()
                
                # Assuming Column A (0) is State, Column B (1) is Cost
                df_slice[1] = df_slice[1].astype(str).str.replace(r'[$, ]', '', regex=True)
                df_slice[1] = pd.to_numeric(df_slice[1], errors='coerce').fillna(0)
                
                # Filter only where cost is greater than 0
                df_filtered = df_slice[df_slice[1] > 0][[0, 1]]
                df_filtered.columns = ["State / Province", "Shipping Cost"]
                
                # Sort from most expensive to least
                df_filtered = df_filtered.sort_values(by="Shipping Cost", ascending=False)
                
                # Add dollar signs for display
                df_filtered["Shipping Cost"] = df_filtered["Shipping Cost"].map("${:,.2f}".format)
                
                st.dataframe(df_filtered, hide_index=True, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error loading Shipping Analysis: {e}")

# --- END OF FILE ---
