import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Styling
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #1f77b4; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- SHEET IDs ---
FORECAST_SHEET_ID = "1elePyM-HdtFc382VsSac8PD4NQrUSXZF9qypCzyzcCc" 
MAIN_SHEET_ID = "1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"

# GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}
GIDS_FOR_MONTHS = {"🇺🇸 US": "2053646844", "🇨🇦 CA": "1132992902", "🇪🇺 EU": "314290170", "🇦🇺 AU": "592032183", "🇬🇧 UK": "1664038544"}
GID_SAFETY_SOURCE = "2100066410"

# --- REGION RANGES FOR SHOPIFY SAFETY STOCK ---
REGION_RANGES = {
    "🇺🇸 US": (1, 21),    # Rows 3-22
    "🇨🇦 CA": (22, 42),   # Rows 24-43
    "🇬🇧 UK": (44, 64),   # Rows 46-65
    "🇪🇺 EU": (66, 86),   # Rows 68-87
    "🇦🇺 AU": (88, 108)   # Rows 90-109
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

# --- SIDEBAR ---
st.sidebar.header("🏢 Channel")
chan = st.sidebar.selectbox("Source", ["Shopify/WH", "Amazon (FBA)"])
st.sidebar.header("📌 Category")
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & Risk Analysis")
    try:
        # Load Inventory
        inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
        df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        m_sel = st.radio("Select Market", list(m_map.keys()), horizontal=True)
        
        s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
        s_df.columns = ["SKU", "Stock"]
        s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
        s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

        # --- RISK ANALYSIS: ONLY FOR SHOPIFY/WH ---
        if chan == "Shopify/WH":
            st.subheader(f"🚨 3-Month Out-of-Stock Risk ({m_sel})")
            # 1. Slice Safety Stock by Region Range
            safety_full = load_csv(FORECAST_SHEET_ID, GID_SAFETY_SOURCE)
            r_start, r_end = REGION_RANGES[m_sel]
            safety_df = safety_full.iloc[r_start:r_end].copy()
            safety_df.columns = [str(c).strip() for c in safety_df.columns]
            
            # 2. Monthly Forecast
            f_df = load_csv(FORECAST_SHEET_ID, GIDS_FOR_MONTHS[m_sel])
            f_df.columns = [str(c).strip() for c in f_df.columns]
            target_months = [(datetime.now().replace(day=1) + timedelta(days=31*i)).replace(day=1).strftime('%Y-%m-01') for i in range(3)]

            risk_data = []
            for _, row in f_df.iterrows():
                sku = str(row.iloc[0]).strip()
                if not is_valid_sku(sku): continue
                demand_3m = sum([pd.to_numeric(row[m], errors='coerce') for m in target_months if m in f_df.columns])
                safe_row = safety_df[safety_df.iloc[:, 0].str.lower().str.strip() == sku.lower()]
                safety = pd.to_numeric(safe_row.iloc[0, 2], errors='coerce') if not safe_row.empty else 0
                live_val = s_df[s_df["SKU"].str.lower().str.strip() == sku.lower()]["Stock"].sum()
                balance = live_val - demand_3m - safety
                if balance < 0:
                    risk_data.append({"SKU": sku.upper(), "Live Stock": int(live_val), "3m Demand": int(demand_3m), "Safety": int(safety), "Shortage": int(abs(balance))})

            if risk_data:
                st.error(f"⚠️ {len(risk_data)} SKUs at risk for {m_sel}.")
                st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
            else: st.success(f"✅ {m_sel} stock levels look healthy.")
            st.divider()

        # Display Stock Tables for Both Shopify and AMZ
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("🎒 Accessories")
            st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

    except Exception as e: st.error(f"Error: {e}")

# --- SALES PERFORMANCE (FULL RESTORATION) ---
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
