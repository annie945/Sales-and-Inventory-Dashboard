import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Setup & Config
st.set_page_config(layout="wide", page_title="Global Inventory & Risk")

# --- SHEET IDs ---
FORECAST_SHEET_ID = "1elePyM-HdtFc382VsSac8PD4NQrUSXZF9qypCzyzcCc" 
MAIN_SHEET_ID = "1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"

# Configuration GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}

# Individual Monthly Demand GIDs
GIDS_FOR_MONTHS = {
    "🇺🇸 US": "2053646844",
    "🇨🇦 CA": "1132992902",
    "🇪🇺 EU": "314290170",
    "🇦🇺 AU": "592032183",
    "🇬🇧 UK": "1664038544"
}
GID_SAFETY_SOURCE = "2100066410" # D2C Stock Forecast Tab

CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]

@st.cache_data(ttl=300)
def load_csv(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def is_cam(s): return any(x in str(s).upper() for x in CAMS)

# --- SIDEBAR ---
st.sidebar.header("🏢 Channel")
chan = st.sidebar.selectbox("Source", ["Shopify/WH", "Amazon (FBA)"])
st.sidebar.header("📌 Category")
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

# --- INVENTORY & RISK ---
if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & 3-Month Risk")
    
    try:
        # 1. Load Main Inventory
        inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
        df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
        
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        m_sel = st.radio("Select Market", list(m_map.keys()), horizontal=True)
        
        s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
        s_df.columns = ["SKU", "Stock"]
        s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

        # 2. Load Forecast Sheets
        safety_df = load_csv(FORECAST_SHEET_ID, GID_SAFETY_SOURCE)
        safety_df.columns = [str(c).strip() for c in safety_df.columns]
        
        f_df = load_csv(FORECAST_SHEET_ID, GIDS_FOR_MONTHS[m_sel])
        f_df.columns = [str(c).strip() for c in f_df.columns]
        
        # 3-Month Logic (Today + Next 2 Months)
        today = datetime.now()
        target_months = [(today.replace(day=1) + timedelta(days=31*i)).replace(day=1).strftime('%Y-%m-01') for i in range(3)]

        st.subheader(f"🚨 3-Month Out-of-Stock Risk ({m_sel})")
        st.caption(f"Analyzing Forecast Demand for: {', '.join(target_months)}")
        
        risk_data = []
        for _, row in f_df.iterrows():
            sku = str(row.iloc[0]).lower().strip()
            # Skip noise rows found in the sheet
            if sku in ['total', 'sku', 'nan', '', 'seasidx', 'nlfd', 'ukfd']: continue
            
            # Demand Sum for 3 months from individual tab
            demand_3m = sum([pd.to_numeric(row[m], errors='coerce') for m in target_months if m in f_df.columns])
            
            # Get Safety Stock (Col C) from GID 2100066410
            safe_row = safety_df[safety_df.iloc[:, 0].str.lower().str.strip() == sku]
            safety = pd.to_numeric(safe_row.iloc[0, 2], errors='coerce') if not safe_row.empty else 0
            
            # Cross reference live stock from Main Inventory Sheet
            live_row = s_df[s_df["SKU"].str.lower().str.strip() == sku]
            live_val = live_row["Stock"].values[0] if not live_row.empty else 0
            
            # The Risk Formula
            balance = live_val - demand_3m - safety
            
            if balance < 0:
                risk_data.append({
                    "SKU": sku.upper(),
                    "Live Stock": int(live_val),
                    "3m Demand": int(demand_3m),
                    "Safety (Col C)": int(safety),
                    "Shortage Qty": int(abs(balance))
                })

        if risk_data:
            st.error(f"⚠️ {len(risk_data)} SKUs estimated to go OOS in {m_sel}.")
            st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage Qty", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.success(f"✅ All {m_sel} stock levels look safe for the next 3 months.")

        st.divider()
        # Live Inventory Tables
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("🎒 Accessories")
            st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Forecast Data Connection Error. Details: {e}")

# --- SALES PERFORMANCE ---
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales")
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
        cur, pre = df[df['date']>=s1].copy(), df[(df['date']>=p1) & (df['date']<=p2)].copy()
        
        st.info(f"📅 Week: {s1} to {lt}")
        col1, col2 = st.columns(2)
        with col1:
            v = cur[cur['sku'].apply(is_cam)]['quantity'].sum()
            o = pre[pre['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("📸 Weekly Camera", int(v), delta=int(v-o))
        with col2:
            v = cur[~cur['sku'].apply(is_cam)]['quantity'].sum()
            o = pre[~pre['sku'].apply(is_cam)]['quantity'].sum()
            st.metric("🎒 Weekly Accessory", int(v), delta=int(v-o))
    except Exception as e: st.error(f"Sales Error: {e}")
