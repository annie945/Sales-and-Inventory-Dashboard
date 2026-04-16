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

# --- REFINED PO FILTERING BY CHANNEL AND REGION ---
def get_filtered_po_data(channel, region_label):
    try:
        df_po = load_csv(PO_MASTER_SHEET_ID, GID_PO_GRID)
        # Column Map: A=PO(0), E=Dest(4), F=SKU(5), G=OrderQty(6), J=ETA(9), K=Track(10), L=Status(11)
        df_po.columns = range(df_po.shape[1])
        
        # 1. Status Check (Exclude Received)
        df_po = df_po[df_po[11].astype(str).str.upper() != "RECEIVED"]
        
        # 2. Channel & Region Keyword Logic for Column E (Destination)
        # Mapping region labels to keywords found in your Destination strings
        region_keys = {
            "🇺🇸 US": "US", "🇨🇦 CA": "CA", "🇬🇧 UK": "UK", 
            "🇦🇺 AU": "AU", "🇪🇺 EU": "EU"
        }
        r_key = region_keys.get(region_label, "")
        
        # Filter for Channel
        if channel == "Amazon (FBA)":
            df_po = df_po[df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
        else:
            df_po = df_po[~df_po[4].astype(str).str.contains("AMZ", case=False, na=False)]
            
        # Filter for specific Region
        df_po = df_po[df_po[4].astype(str).str.contains(r_key, case=False, na=False)]
            
        df_po = df_po[[0, 5, 6, 9, 10]] 
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
        # Load Inventory Settings
        inv_gid = "856174189" if chan == "Amazon (FBA)" else "0"
        df_inv = load_csv(MAIN_SHEET_ID, inv_gid)
        m_map = {"🇺🇸 US": 4, "🇨🇦 CA": 11, "🇬🇧 UK": 25, "🇦🇺 AU": 18} if chan == "Amazon (FBA)" else {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        m_sel = st.radio("Select Market", list(m_map.keys()), horizontal=True)
        
        # 1. INBOUND PIPELINE (Filtered by Region keyword in Col E)
        st.subheader(f"🚚 Incoming Orders for {m_sel} ({chan})")
        df_po_filtered = get_filtered_po_data(chan, m_sel)
        
        if not df_po_filtered.empty:
            po_display = df_po_filtered.groupby('SKU').agg({
                'Qty': 'sum',
                'PO': lambda x: ', '.join(x.unique()),
                'ETA': lambda x: ', '.join(x.dropna().unique()),
                'Tracking': lambda x: ', '.join(x.dropna().astype(str).unique())
            }).rename(columns={'Qty': 'Total Incoming'}).reset_index()
            st.dataframe(po_display, use_container_width=True, hide_index=True)
            po_summary = df_po_filtered.groupby('SKU')['Qty'].sum().reset_index()
        else:
            st.info(f"No pending orders currently destined for {m_sel}.")
            po_summary = pd.DataFrame(columns=['SKU', 'Qty'])

        st.divider()

        # 2. STOCK PROCESSING
        s_df = df_inv.iloc[:, [0, m_map[m_sel]]].copy()
        s_df.columns = ["SKU", "Stock"]
        s_df = s_df[s_df["SKU"].apply(is_valid_sku)]
        s_df["Stock"] = pd.to_numeric(s_df["Stock"], errors='coerce').fillna(0).astype(int)
        
        # Merge Inbound with Live Stock
        s_df = pd.merge(s_df, po_summary, on='SKU', how='left').fillna(0)
        s_df.rename(columns={'Qty': 'On Order'}, inplace=True)

        # 3. RISK ANALYSIS
        if m_sel in GIDS_FOR_MONTHS[chan]:
            st.subheader(f"🚨 Risk Analysis (Live + Incoming)")
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
                inbound_val = item_row["On Order"].sum()
                
                balance = (live_val + inbound_val) - demand_3m - safety
                
                if balance < 0:
                    risk_data.append({
                        "SKU": sku.upper(), 
                        "Stock": int(live_val), 
                        "Incoming": int(inbound_val),
                        "Shortage": int(abs(balance))
                    })

            if risk_data:
                st.error(f"⚠️ {len(risk_data)} SKUs remain at risk even with incoming stock.")
                st.dataframe(pd.DataFrame(risk_data).sort_values(by="Shortage", ascending=False), use_container_width=True, hide_index=True)
            else: st.success(f"✅ All {m_sel} stock requirements met.")
            st.divider()

        # 4. TABLES
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📸 Cameras")
            st.dataframe(s_df[s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("🎒 Accessories")
            st.dataframe(s_df[~s_df["SKU"].apply(is_cam)], hide_index=True, use_container_width=True)

    except Exception as e: st.error(f"Error: {e}")

# (Sales Performance section remains untouched)
elif page == "💰 Sales Performance":
    st.title(f"💰 {chan} Sales Performance")
    # ... [Previous Sales Performance Code Here] ...
