import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. SETUP
st.set_page_config(layout="wide")

B = "https://docs.google.com/spreadsheets/d/1oXGTHDhdnxj99q7vXLe3S2TliT04picEzPdCgtNzaYs/export?format=csv"
G = {
    "🇺🇸 US": "1304392959",
    "🇨🇦 CA": "634720426",
    "🇬🇧 UK": "1657555313",
    "🇦🇺 AU": "1871282385",
    "🇪🇺 EU": "975667344"
}
C = ["MA-HK","MA-KRM","MA-CMR","MA-MN","MA-MK","MC-MIKAYO","MC-AKITO",
     "MK-MEOWIE","MK-ZIPPY","MK-SP","MP-KOKO","MP-HK","MP-KRM","MP-CMR",
     "MP2-BLUE","MP2-MINT","MP2-SP","MP2-WP","MV-IRIS","MV-IRI"]
A = ["MP2-PP-40","MP2-PP-120","MICROSD-32","MP-PAPER","TML-TML-SPROUT",
     "BAG-UNICORN","BAG-KMTGREEN","BAG-LITTLEBEE","BAG-HK","BAG-KRM",
     "BAG-CMR","LANYARD-GREEN","LANYARD-PINK","LANYARD-RED","LANYARD-PURPLE"]

@st.cache_data(ttl=300)
def load(gid):
    u = f"{B}&gid={gid}"
    return pd.read_csv(u)

pg = st.sidebar.radio("Nav", ["📦 Inv", "💰 Sales"])

# --- INVENTORY ---
if pg == "📦 Inv":
    st.title("📦 Inventory")
    try:
        df = load("0")
        m = st.radio("Market", list(G.keys()), horizontal=True)
        mp = {"🇺🇸 US":7,"🇨🇦 CA":15,"🇬🇧 UK":22,"🇦🇺 AU":29,"🇪🇺 EU":38}
        idx = mp[m]
        df_i = df.iloc[:, [0, idx]].copy()
        df_i.columns = ["SKU", "Qty"]
        df_i = df_i.dropna(subset=["SKU"])
        df_i["Qty"] = pd.to_numeric(df_i["Qty"], errors='coerce').fillna(0).astype(int)
        
        c1, c2 = st.columns(2)
        with c1:
            sc = df_i[df_i["SKU"].isin(C)]
            st.metric("Cameras", f"{sc['Qty'].sum():,}")
            st.dataframe(sc, hide_index=True)
        with c2:
            sa = df_i[df_i["SKU"].isin(A)]
            st.metric("Accessories", f"{sa['Qty'].sum():,}")
            st.dataframe(sa, hide_index=True)
    except Exception as e:
        st.error(e)

# --- SALES ---
elif pg == "💰 Sales":
    st.title("💰 Sales")
    r = st.sidebar.selectbox("Region", list(G.keys()))
    try:
        raw = load(G[r])
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['date'] = pd.to_datetime(raw['date']).dt.date
        f = raw[~raw['sku'].str.contains('unknown|worry|delivery', case=False, na=False)]
        
        lt = f['date'].max()
        s1 = lt - timedelta(6)
        p1, p2 = s1 - timedelta(7), s1 - timedelta(1)
        
        cur = f[(f['date'] >= s1) & (f['date'] <= lt)].copy()
        pre = f[(f['date'] >= p1) & (f['date'] <= p2)].copy()
        ytd = f[pd.to_datetime(f['date']).dt.year == lt.year].copy()

        st.write(f"Week: {s1} to {lt}")
        col1, col2 = st.columns(2)
        with col1:
            # ULTRA SHORT LINES
            v = cur[cur['sku'].isin(C)]['quantity'].sum()
            o = pre[pre['sku'].isin(C)]['quantity'].sum()
            st.metric("📸 Cam Week", int(v), delta=int(v-o))
        with col2:
            v = cur[cur['sku'].isin(A)]['quantity'].sum()
            o = pre[pre['sku'].isin(A)]['quantity'].sum()
            st.metric("🎒 Acc Week", int(v), delta=int(v-o))

        st.divider()
        st.subheader("🔥 Weekly Movers")
        r_s = cur.groupby('sku')['quantity'].sum()
        p_s = pre.groupby('sku')['quantity'].sum()
        cp = pd.merge(r_s, p_s, on='sku', how='outer', suffixes=('_c', '_p')).fillna(0)
        cp['D'] = cp['quantity_c'] - cp['quantity_p']
        
        m1, m2, m3, m4 = st.columns(4)
        cm = cp[cp.index.isin(C)]
        ac = cp[cp.index.isin(A)]
        
        with m1:
            st.success("📈 Cam Inc")
            st.dataframe(cm[cm['D']>0].nlargest(3,'D')[['D']])
        with m2:
            st.error("📉 Cam Dec")
            st.dataframe(cm[cm['D']<0].nsmallest(3,'D')[['D']])
        with m3:
            st.success("📈 Acc Inc")
            st.dataframe(ac[ac['D']>0].nlargest(3,'D')[['D']])
        with m4:
            st.error("📉 Acc Dec")
            st.dataframe(ac[ac['D']<0].nsmallest(3,'D')[['D']])

        st.divider()
        st.subheader(f"🏆 YTD {lt.year} Top 3")
        y1, y2 = st.columns(2)
        with y1:
            st.info("📸 Camera YTD")
            yc = ytd[ytd['sku'].isin(C)].groupby('sku')['quantity'].sum()
            st.dataframe(yc.nlargest(3), use_container_width=True)
        with y2:
            st.info("🎒 Accessory YTD")
            ya = ytd[ytd['sku'].isin(A)].groupby('sku')['quantity'].sum()
            st.dataframe(ya.nlargest(3), use_container_width=True)
    except Exception as e:
        st.error(e)

# END OF FILE
