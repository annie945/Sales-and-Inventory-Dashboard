import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- IDs ---
FORECAST_SHEET_ID = "1elePyM-HdtFc382VsSac8PD4NQrUSXZF9qypCzyzcCc" 
MAIN_SHEET_ID = "1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs"

BASE_MAIN = f"https://docs.google.com/spreadsheets/d/{MAIN_SHEET_ID}/export?format=csv"
BASE_FORECAST = f"https://docs.google.com/spreadsheets/d/{FORECAST_SHEET_ID}/export?format=csv"

# Configuration GIDs
GIDS_ORIG = {"🇺🇸 US": "1304392959", "🇨🇦 CA": "634720426", "🇬🇧 UK": "1657555313", "🇦🇺 AU": "1871282385", "🇪🇺 EU": "975667344"}
GIDS_AMZ = {"🇺🇸 US": "1758192113", "🇨🇦 CA": "297394922", "🇬🇧 UK": "1202968115", "🇦🇺 AU": "1435942430"}

# Individual Forecast GIDs
GIDS_FOR_MONTHS = {"🇺🇸 US": "2053646844", "🇨🇦 CA": "1132992902", "🇪🇺 EU": "314290170", "🇦🇺 AU": "592032183", "🇬🇧 UK": "1664038544"}
GID_SAFETY_SOURCE = "1304392959" # D2C Stock Forecast Tab

CAMS = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO","MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR","MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]

@st.cache_data(ttl=300)
def load_main(gid): return pd.read_csv(f"{BASE_MAIN}&gid={gid}")

@st.cache_data(ttl=300)
def load_forecast(gid): return pd.read_csv(f"{BASE_FORECAST}&gid={gid}")

def is_cam(s): return any(x in str(s).upper() for x in CAMS)

# --- SIDEBAR ---
st.sidebar.header("🏢 Channel")
chan = st.sidebar.selectbox("Source", ["Shopify/WH", "Amazon (FBA)"])
st.sidebar.header("📌 Category")
page = st.sidebar.radio("View", ["📦 Inventory & Risk", "💰 Sales Performance"])

if page == "📦 Inventory & Risk":
    st.title(f"📦 {chan} Inventory & 3-Month Risk Analysis")
    
    try:
        # 1. Load Main Inventory
        df_inv = load_main("856174189" if chan == "Amazon (FBA)" else "0")
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        
        m_sel = st.radio("Select Market", list(m_map.keys()), horizontal=True)
        s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
        s_df.columns = ["SKU", "Stock"]
        s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)

        # 2. Load Safety Stock (Fixed Col C from D2C Tab)
        safety_df = load_forecast(GID_SAFETY_SOURCE)
        safety_df.columns = [str(c).strip() for c in safety_df.columns]
        
        # 3. Load 3-Month Demand (Monthly Tabs)
        f_df = load_forecast(GIDS_FOR_MONTHS[m_sel])
        f_df.columns = [str(c).strip() for c in f_df.columns]
        
        # Determine current month + 2
        today = datetime.now()
        target_months = [(today.replace(day=1) + timedelta(days=31*i)).replace(day=1).strftime('%Y-%m-01') for i in range(3)]

        st.subheader(f"🚨 3-Month OOS Risk Alert ({m_sel})")
        
        risk_data = []
        for _, row in f_df.iterrows():
            sku = str(row.iloc[0]).lower().strip()
            if sku in ['total', 'sku', 'nan', '', 'seasidx']: continue
            
            # Demand Sum
            demand_3m = sum([pd.to_numeric(row[m], errors='coerce') for m in target_months if m in f_df.columns])
            
            # Get Safety Stock from D2C Tab (Matching SKU)
            safe_row = safety_df[safety_df.iloc[:, 0].str.lower().str.strip() == sku]
            safety = pd.to_numeric(safe_row.iloc[0, 2], errors='coerce') if not safe_row.empty else 0
            
            # Get Live Stock
            live_row = s_df[s_df["SKU"].str.lower().str.strip() == sku]
            live_val = live_row["Stock"].values[0] if not live_row.empty else 0
            
            balance = live_val - demand_3m - safety
            
            if balance < 0:
                risk_data.append({
                    "SKU": sku.upper(),
                    "Live Stock": int(live_val),
                    "3m Demand": int(demand_3m),
                    "Safety (Col C)": int(safety),
                    "Shortage": int(abs(balance))
                })

        if risk_data:
            st.error(f"⚠️ Warning: {len(risk_data)} SKUs estimated to go OOS.")
            st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Stock levels are healthy.")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("🎒 Accessories")
            st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading Forecast data: {e}")

# (Sales Performance page logic follows here, remains unchanged)
