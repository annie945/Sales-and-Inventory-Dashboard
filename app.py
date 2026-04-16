import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")

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
    # DELETE WORRY FREE DELIVERY and other noise
    if any(x in s for x in ["WORRY FREE", "DELIVERY", "PROTECTION", "NAN", "TOTAL", "HEALTH"]): return False
    if s == "": return False
    return any(x in s for x in CAMS + ACCS)

def is_cam(s): return any(x in str(s).upper() for x in CAMS)

def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        df_po.columns = range(df_po.shape[1])
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        region_map = {"🇺🇸 US": ["US"], "🇨🇦 CA": ["CA"], "🇬🇧 UK": ["UK"], "🇦🇺 AU": ["AU"], "🇪🇺 EU": ["EU", "Germany"]}
        keywords = region_map.get(region_label, [])
        if channel == "Amazon (FBA)":
            df_po = df_po[df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
        else:
            df_po = df_po[~df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
        pattern = '|'.join(keywords)
        df_po = df_po[df_po[4].astype(str).str.contains(pattern, case=False, na=False)]
        return df_po[[0, 5, 6, 9, 10]].rename(columns={0:'PO', 5:'SKU', 6:'Qty', 9:'ETA', 10:'Tracking'})
    except: return pd.DataFrame()

# --- SIDEBAR ---
chan = st.sidebar.selectbox("Channel", ["Shopify/WH", "Amazon (FBA)"])
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- INVENTORY & RISK (UNTOUCHED) ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk")
    m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
    m_sel = st.radio("Market", list(m_map.keys()), horizontal=True)
    
    df_po = get_filtered_po_data(chan, m_sel)
    po_summary = pd.DataFrame(columns=['SKU', 'Qty'])
    if not df_po.empty:
        st.subheader("🚚 Inbound Pipeline")
        st.dataframe(df_po, use_container_width=True, hide_index=True)
        po_summary = df_po.groupby('SKU')['Qty'].sum().reset_index()

    if m_sel in GIDS_FOR_MONTHS[chan]:
        st.subheader(f"🚨 3-Month Out-of-Stock Risk ({m_sel})")
        try:
            safety_full = load_csv(FORECAST_SHEET_ID, GID_SAFETY_SOURCE)
            r_start, r_end = REGION_RANGES[chan][m_sel]
            safety_df = safety_full.iloc[r_start:r_end].copy()
            safety_df.columns = [str(c).strip() for c in safety_df.columns]
            f_df = load_csv(FORECAST_SHEET_ID, GIDS_FOR_MONTHS[chan][m_sel])
            f_df.columns = [str(c).strip() for c in f_df.columns]
            target_months = [(datetime.now().replace(day=1) + timedelta(days=31*i)).replace(day=1).strftime('%Y-%m-01') for i in range(3)]
            df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
            s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
            s_df.columns = ["SKU", "Stock"]
            s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

            risk_data = []
            for _, row in f_df.iterrows():
                sku = str(row.iloc[0]).strip()
                if not is_valid_sku(sku): continue
                demand_3m = sum([pd.to_numeric(row[m], errors='coerce') for m in target_months if m in f_df.columns])
                safe_row = safety_df[safety_df.iloc[:, 0].str.lower().str.strip() == sku.lower()]
                safety_val = pd.to_numeric(safe_row.iloc[0, 2], errors='coerce') if not safe_row.empty else 0
                live_val = s_df[s_df["SKU"].str.lower().str.strip() == sku.lower()]["Stock"].sum()
                inbound_val = po_summary[po_summary["SKU"].str.lower().str.strip() == sku.lower()]["Qty"].sum()
                balance = (live_val + inbound_val) - demand_3m - safety_val
                if balance < 0:
                    risk_data.append({"SKU": sku.upper(), "Stock": int(live_val), "Inbound": int(inbound_val), "3m Demand": int(demand_3m), "Shortage": int(abs(balance))})
            if risk_data:
                st.error(f"⚠️ {len(risk_data)} SKUs at risk.")
                st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
            else: st.success(f"✅ Demand met.")
        except Exception as e: st.warning(f"Risk calculation unavailable.")
    st.divider()

    df_inv = load_csv(MAIN_SHEET_ID, "856174189" if chan == "Amazon (FBA)" else "0")
    s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
    s_df.columns = ["SKU", "Stock"]
    s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
    c1, c2 = st.columns(2)
    with c1: st.subheader("📸 Cameras"); st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
    with c2: st.subheader("🎒 Accessories"); st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

# --- SALES PERFORMANCE (UPDATED) ---
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
        
        # APPLY FILTER TO DELETE WORRY FREE & OTHERS
        df = df[df['sku'].apply(is_valid_sku)]
        df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
        df = df.dropna(subset=['date'])
        
        lt = df['date'].max()
        s1, p1, p2 = lt - timedelta(6), lt - timedelta(13), lt - timedelta(7)
        curr, prev = df[df['date'] >= s1], df[(df['date'] >= p1) & (df['date'] <= p2)]
        
        col1, col2 = st.columns(2)
        with col1:
            v, o = curr[curr['sku'].apply(is_cam)]['quantity'].sum(), prev[prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Weekly Cameras", int(v), delta=int(v-o))
        with col2:
            v, o = curr[~curr['sku'].apply(is_cam)]['quantity'].sum(), prev[~prev['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("🎒 Weekly Accessories", int(v), delta=int(v-o))
        
        st.divider()
        st.subheader("🔥 Weekly Movers (vs Prev Week)")
        
        r_s, p_s = curr.groupby('sku')['quantity'].sum(), prev.groupby('sku')['quantity'].sum()
        cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        cp['D'] = cp['quantity_c'] - cp['quantity_p']
        
        # FILTER OUT 0 QTY
        cp = cp[cp['quantity_c'] > 0]
        
        cm, ac = cp[cp.index.map(is_cam)], cp[~cp.index.map(is_cam)]
        
        # 2x2 GRID FOR TOP/BOTTOM 3
        m1, m2 = st.columns(2)
        with m1:
            st.success("📸 Cameras: Top 3 Increase")
            st.dataframe(cm[cm['D']>0].nlargest(3,'D')[['D']], use_container_width=True)
            st.error("📸 Cameras: Bottom 3 Decrease")
            st.dataframe(cm[cm['D']<0].nsmallest(3,'D')[['D']], use_container_width=True)
        with m2:
            st.success("🎒 Accessories: Top 3 Increase")
            st.dataframe(ac[ac['D']>0].nlargest(3,'D')[['D']], use_container_width=True)
            st.error("🎒 Accessories: Bottom 3 Decrease")
            st.dataframe(ac[ac['D']<0].nsmallest(3,'D')[['D']], use_container_width=True)
            
    except Exception as e: st.error(f"Sales Error: {e}")
