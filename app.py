import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #1f77b4; }
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] { background-color: #f1f3f6; }
    </style>
    """, unsafe_allow_html=True)

# --- SHEET IDs ---
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

# --- REGION RANGES FOR SAFETY STOCK ---
REGION_RANGES = {
    "Shopify/WH": {"🇺🇸 US": (1, 21), "🇨🇦 CA": (22, 42), "🇬🇧 UK": (44, 64), "🇪🇺 EU": (66, 86), "🇦🇺 AU": (88, 108)},
    "Amazon (FBA)": {"🇺🇸 US": (110, 130), "🇨🇦 CA": (131, 151)}
}

CAMS = ["MA-","MC-","MK-","MP-","MV-"]
ACCS = ["MP2-","MICROSD","TML-","BAG-","LANYARD"]

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_valid_sku(s):
    s = str(s).upper().strip()
    noise = ["RISK", "ATTENTION", "HEALTH", "NONE", "SKU", "TOTAL", "SEASIDX", "NLFD", "UKFD", "SFUS", "SFCA", "AUNPF"]
    if any(x == s for x in noise) or s == "" or "NAN" in s: return False
    return any(x in s for x in CAMS + ACCS)

def is_cam(s): return any(x in str(s).upper() for x in CAMS)

# --- PO DATA PROCESSING ---
def get_on_order_data(channel_filter):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        # Column Map: A=PO(0), E=Dest(4), F=SKU(5), G=OrderQty(6), H=ShipQty(7), J=ETA(9), K=Track(10), L=Status(11)
        df_po.columns = range(df_po.shape[1])
        
        # Filter 1: Exclude 'Received'
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        
        # Filter 2: Split by Destination
        if channel_filter == "Amazon (FBA)":
            df_po = df_po[df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
        else:
            df_po = df_po[~df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
            
        # Select relevant columns for grouping
        df_po = df_po[[0, 5, 6, 9, 10]] # PO, SKU, Qty, ETA, Tracking
        df_po.columns = ['PO', 'SKU', 'Qty', 'ETA', 'Tracking']
        df_po['Qty'] = pd.to_numeric(df_po['Qty'], errors='coerce').fillna(0)
        
        return df_po
    except:
        return pd.DataFrame(columns=['PO', 'SKU', 'Qty', 'ETA', 'Tracking'])

# --- SIDEBAR ---
st.sidebar.header("🏢 Channel")
chan = st.sidebar.selectbox("Source", ["Shopify/WH", "Amazon (FBA)"])
st.sidebar.header("📌 Category")
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    try:
        # Load Inventory
        inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
        df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        m_sel = st.radio("Select Market", list(m_map.keys()), horizontal=True)
        
        # 1. NEW SECTION: VISIBLE ON-ORDER TRACKER
        st.subheader(f"🚚 Inbound Pipeline (On Order for {chan})")
        df_po_raw = get_on_order_data(chan)
        
        if not df_po_raw.empty:
            # Group for the Risk engine
            po_summary = df_po_raw.groupby('SKU')['Qty'].sum().reset_index()
            # Group for the display table
            po_display = df_po_raw.groupby('SKU').agg({
                'Qty': 'sum',
                'PO': lambda x: ', '.join(x.unique()),
                'ETA': lambda x: ', '.join(x.dropna().unique()),
                'Tracking': lambda x: ', '.join(x.dropna().astype(str).unique())
            }).rename(columns={'Qty': 'Total Incoming'}).reset_index()
            
            st.dataframe(po_display, use_container_width=True, hide_index=True)
        else:
            st.write("No active POs found for this channel.")
        
        st.divider()

        # 2. STOCK PROCESSING
        s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
        s_df.columns = ["SKU", "Stock"]
        s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
        s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
        
        # Merge with Inbound totals
        if not df_po_raw.empty:
            s_df = pd.merge(s_df, po_summary, on='SKU', how='left').fillna(0)
            s_df.rename(columns={'Qty': 'Inbound'}, inplace=True)
        else:
            s_df['Inbound'] = 0

        # 3. RISK ANALYSIS (Uses Stock + Inbound)
        if m_sel in GIDS_FOR_MONTHS[chan]:
            st.subheader(f"🚨 3-Month Out-of-Stock Risk ({m_sel})")
            safety_full = load_csv(FORECAST_SHEET_ID, GID_SAFETY_SOURCE)
            r_start, r_end = REGION_RANGES[chan][m_sel]
            safety_df = safety_full.iloc[r_start:r_end].copy()
            safety_df.columns = [str(c).strip() for c in safety_df.columns]
            
            f_df = load_csv(FORECAST_SHEET_ID, GIDS_FOR_MONTHS[chan][m_sel])
            f_df.columns = [str(c).strip() for c in f_df.columns]
            target_months = [(datetime.now().replace(day=1) + timedelta(days=31*i)).replace(day=1).strftime('%Y-%m-01') for i in range(3)]

            risk_data = []
            for _, row in f_df.iterrows():
                sku = str(row.iloc[0]).strip()
                if not is_valid_sku(sku): continue
                demand_3m = sum([pd.to_numeric(row[m], errors='coerce') for m in target_months if m in f_df.columns])
                safe_row = safety_df[safety_df.iloc[:, 0].str.lower().str.strip() == sku.lower()]
                safety = pd.to_numeric(safe_row.iloc[0, 2], errors='coerce') if not safe_row.empty else 0
                
                item_row = s_df[s_df["SKU"].str.lower().str.strip() == sku.lower()]
                live_val = item_row["Stock"].sum()
                inbound_val = item_row["Inbound"].sum()
                
                balance = (live_val + inbound_val) - demand_3m - safety
                
                if balance < 0:
                    risk_data.append({
                        "SKU": sku.upper(), 
                        "Live Stock": int(live_val), 
                        "📦 Inbound": int(inbound_val),
                        "3m Demand": int(demand_3m), 
                        "Shortage": int(abs(balance))
                    })

            if risk_data:
                st.error(f"⚠️ {len(risk_data)} SKUs at risk (Shortage after Inbound arrives).")
                st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
            else: st.success(f"✅ All stock levels healthy.")
            st.divider()

        # 4. MAIN INVENTORY TABLES
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("🎒 Accessories")
            st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

    except Exception as e: st.error(f"Error: {e}")

# --- SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    active_gids = GIDS_AMZ if chan == "Amazon (FBA)" else GIDS_ORIG
    reg = st.sidebar.selectbox("Region", list(active_gids.keys()))
    try:
        df = load_csv(MAIN_SHEET_ID, active_gids[reg])
        df.columns = [str(col).strip().lower() for col in df.columns]
        s_col = next((c for c in df.columns if 'sku' in c), 'sku')
        q_col = next((c for c in df.columns if 'qty' in c or 'quantity' in c), 'quantity')
        d_col = next((c for c in df.columns if 'date' in c), 'date')
        df = df.rename(columns={s_col: 'sku', q_col: 'quantity', d_col: 'date'})
        df['date'] = pd.to_datetime(df['date'], format='mixed').dt.date
        
        lt = df['date'].max()
        s1, p1, p2 = lt - timedelta(6), lt - timedelta(13), lt - timedelta(7)
        curr, prev = df[df['date']>=s1].copy(), df[(df['date']>=p1) & (df['date']<=p2)].copy()
        ytd_df = df[pd.to_datetime(df['date']).dt.year == lt.year].groupby('sku')['quantity'].sum().reset_index()

        st.info(f"📅 Week: {s1} to {lt} vs {p1} to {p2}")
        col1, col2 = st.columns(2)
        with col1:
            v, o = curr[curr['sku'].apply(is_cam)]['quantity'].sum(), prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Weekly Camera", int(v), delta=int(v-o))
        with col2:
            v, o = curr[~curr['sku'].apply(is_cam)]['quantity'].sum(), prev[prev['sku'].apply(is_cam) == False]['quantity'].sum()
            st.metric("🎒 Weekly Accessory", int(v), delta=int(v-o))

        st.divider()
        st.subheader("🔥 Weekly Top Movers")
        r_s, p_s = curr.groupby('sku')['quantity'].sum(), prev.groupby('sku')['quantity'].sum()
        cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        cp['D'] = cp['quantity_c'] - cp['quantity_p']
        m1, m2, m3, m4 = st.columns(4)
        cm, ac = cp[cp.index.map(is_cam)], cp[cp.index.map(is_cam) == False]
        with m1:
            st.success("📈 Cam Increase")
            st.dataframe(cm[cm['D']>0].nlargest(3,'D')[['D']], use_container_width=True)
        with m2:
            st.error("📉 Cam Decrease")
            st.dataframe(cm[cm['D']<0].nsmallest(3,'D')[['D']], use_container_width=True)
        with m3:
            st.success("📈 Acc Increase")
            st.dataframe(ac[ac['D']>0].nlargest(3,'D')[['D']], use_container_width=True)
        with m4:
            st.error("📉 Acc Decrease")
            st.dataframe(ac[ac['D']<0].nsmallest(3,'D')[['D']], use_container_width=True)

        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top 3 Sellers")
        y1, y2 = st.columns(2)
        with y1:
            st.info("📸 Camera Top 3 (YTD)")
            st.dataframe(ytd_df[ytd_df['sku'].apply(is_cam)].nlargest(3,'quantity'), hide_index=True, use_container_width=True)
        with y2:
            st.info("🎒 Accessory Top 3 (YTD)")
            st.dataframe(ytd_df[ytd_df['sku'].apply(is_cam) == False].nlargest(3,'quantity'), hide_index=True, use_container_width=True)
    except Exception as e: st.error(f"Sales Error: {e}")
