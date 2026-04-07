import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 1. 頁面配置 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #1f2937; padding: 10px; border-radius: 12px; border: 1px solid #4ade80; 
    }
    .stNumberInput input { font-size: 20px !important; font-weight: bold; color: #4ade80 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if st.sidebar.button("🚨 系統修復"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

# --- 3. 穩定讀取 ---
def load_data_v12(worksheet_name, standard_cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        if df is None or df.empty: return pd.DataFrame(columns=standard_cols)
        df.columns = standard_cols[:len(df.columns)]
        return df
    except: return pd.DataFrame(columns=standard_cols)

COL_S = ["球種", "單筒價格", "單價"]
COL_R = ["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"]

settings_df = load_data_v12("Settings", COL_S)
records_df = load_data_v12("Records", COL_R)
ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []

st.title("🏸 羽球管家 Pro")
t1, t2, t3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史與編輯"])

# --- TAB 1: 新增開團 (一小時制) ---
with t1:
    if 'ball_usage' not in st.session_state:
        st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": ball_options[0] if ball_options else "", "count": 0}]
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1: 
            date = st.date_input("🗓️ 日期", datetime.now(), key="add_date")
        with c2:
            # 以一小時為單位
            hours = st.number_input("⏰ 場地小時數", min_value=1.0, value=2.0, step=1.0, key="add_hours")
            court_f = int(hours * 250)
            st.success(f"🏟️ 場地費自動計算: ${court_f} ({int(hours)}hr x 250)")
        
        st.write("---")
        st.write("#### 💰 收入人數")
        i1, i2, i3 = st.columns(3)
        with i1: p140 = st.number_input("$140", min_value=0, key="a140")
        with i2: p180 = st.number_input("$180", min_value=0, key="a180")
        with i3: p240 = st.number_input("$240", min_value=0, key="a240")
        total_in = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 目前總收入：**${total_in}**")
        
        if ball_options:
            st.write("---")
            st.write("#### 🎾 用球明細")
            total_b_cost, details = 0.0, []
            for idx, row in enumerate(st.session_state.ball_usage):
                uid = row.get("id")
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    b_idx = ball_options.index(row['ball_type']) if row['ball_type'] in ball_options else 0
                    row['ball_type'] = st.selectbox("球種", ball_options, index=b_idx, key=f"at_{uid}", label_visibility="collapsed")
                with r2: 
                    row['count'] = st.number_input("顆數", min_value=0, value=row['count'], key=f"an_{uid}", label_visibility="collapsed")
                with r3:
                    if st.button("❌", key=f"ad_{uid}"):
                        st.session_state.ball_usage.pop(idx); st.rerun()
                up = float(settings_df.loc[settings_df["球種"] == row['ball_type'], "單價"].values[0])
                total_b_cost += up * row['count']
                if row['count'] > 0: details.append(f"{row['ball_type']}x{row['count']}")
            
            if st.button("➕ 新增球種項目", key="add_row"):
                st.session_state.ball_usage.append({"id": str(time.time()), "ball_type": ball_options[0], "count": 0}); st.rerun()
            
            net = total_in - (court_f + total_b_cost)
            st.write("---")
            if st.button("🚀 儲存今日紀錄", use_container_width=True):
                new_d = pd.DataFrame([[str(date), int(court_f), ", ".join(details), round(total_b_cost, 1), int(total_in), round(net, 1)]], columns=COL_R)
                conn.update(worksheet="Records", data=pd.concat([records_df, new_d], ignore_index=True))
                st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": ball_options[0], "count": 0}]; st.success("已存檔！"); time.sleep(1); st.rerun()

# --- TAB 2 & 3 ---
with t2:
    st.dataframe(settings_df, use_container_width=True)
    with st.form("set_b"):
        name = st.text_input("球種名稱")
        price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存球種"):
            if name and price > 0:
                new_b = pd.DataFrame([[name, price, round(price/12, 2)]], columns=COL_S)
                conn.update(worksheet="Settings", data=pd.concat([settings_df, new_b], ignore_index=True)); st.rerun()

with t3:
    if not records_df.empty:
        df_view = records_df.copy()
        df_view.index = range(1, len(df_view) + 1)
        st.dataframe(df_view.sort_index(ascending=False), use_container_width=True)
        st.divider()
        st.subheader("✏️ 快速修改選單")
        options = [f"{i+1}: {records_df.iloc[i,0]} (總收${records_df.iloc[i,4]})" for i in range(len(records_df))]
        selected = st.selectbox("請選擇要編輯的場次", options=options[::-1], key="v12_selector")
        sel_idx = int(selected.split(":")[0]) - 1
        target = records_df.iloc[sel_idx].tolist()

        with st.expander(f"🛠️ 編輯中：{selected}", expanded=True):
            c_key = f"cache_v12_{sel_idx}"
            if c_key not in st.session_state:
                items = []
                raw = str(target[2])
                if raw and raw != "nan":
                    for p in raw.split(", "):
                        if 'x' in p:
                            try:
                                n_p, c_p = p.split('x')
                                items.append({"id": f"e{time.time()}{p}", "ball_type": n_p, "count": int(c_p)})
                            except: pass
                if not items: items = [{"id": f"e{time.time()}", "ball_type": ball_options[0] if ball_options else "", "count": 0}]
                st.session_state[c_key] = items

            e_date = st.date_input("日期", datetime.strptime(str(target[0]), '%Y-%m-%d'), key=f"ev_d_{sel_idx}")
            e_court = st.number_input("場地費總額", value=int(target[1]), key=f"ev_c_{sel_idx}")
            e_income = st.number_input("總收入", value=int(target[4]), key=f"ev_i_{sel_idx}")

            st.write("**🎾 用球數量修改**")
            e_b_cost, e_details = 0.0, []
            for idx, item in enumerate(st.session_state[c_key]):
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    b_idx = ball_options.index(item['ball_type']) if item['ball_type'] in ball_options else 0
                    item['ball_type'] = st.selectbox("球種", ball_options, index=b_idx, key=f"evt_{sel_idx}_{idx}")
                with r2: item['count'] = st.number_input("顆數", min_value=0, value=item['count'], key=f"evn_{sel_idx}_{idx}")
                with r3:
                    if st.button("❌", key=f"evd_{sel_idx}_{idx}"):
                        st.session_state[c_key].pop(idx); st.rerun()
                up_row = settings_df.loc[settings_df["球種"] == item['ball_type'], "單價"]
                up = float(up_row.values[0]) if not up_row.empty else 0.0
                e_b_cost += up * item['count']
                if item['count'] > 0: e_details.append(f"{item['ball_type']}x{item['count']}")

            if st.button("➕ 新增球種項目", key=f"eva_{sel_idx}"):
                st.session_state[c_key].append({"id": str(time.time()), "ball_type": ball_options[0], "count": 0}); st.rerun()

            e_net = e_income - (e_court + e_b_cost)
            st.warning(f"📊 試算：成本 ${e_court + e_b_cost:.1f} / 淨利 ${e_net:.1f}")

            btn_save, btn_del = st.columns(2)
            with btn_save:
                if st.button("💾 儲存修改", use_container_width=True, key=f"evs_{sel_idx}"):
                    records_df.iloc[sel_idx] = [str(e_date), int(e_court), ", ".join(e_details), round(e_b_cost, 1), int(e_income), round(e_net, 1)]
                    conn.update(worksheet="Records", data=records_df); st.rerun()
            with btn_del:
                if st.button("🗑️ 刪除紀錄", use_container_width=True, key=f"evdel_{sel_idx}"):
                    conn.update(worksheet="Records", data=records_df.drop(records_df.index[sel_idx])); st.rerun()
