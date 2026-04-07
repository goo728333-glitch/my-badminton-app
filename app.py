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
    .stNumberInput input { font-size: 18px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if st.sidebar.button("🚨 系統修復/重新載入"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

# --- 3. 穩定讀取函數 ---
def load_data_stable(worksheet_name, cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=cols)
        # 強制修正欄位名稱，防止 KeyError
        if len(df.columns) >= len(cols):
            df.columns = cols[:len(df.columns)]
        return df
    except:
        return pd.DataFrame(columns=cols)

# 定義標準欄位名稱
COL_SETTINGS = ["球種", "單筒價格", "單價"]
COL_RECORDS = ["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"]

settings_df = load_data_stable("Settings", COL_SETTINGS)
records_df = load_data_stable("Records", COL_RECORDS)

st.title("🏸 羽球管家 Pro")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄 / 編輯"])

# --- TAB 1: 新增開團 ---
with tab1:
    if 'ball_usage' not in st.session_state:
        st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": "", "count": 0}]
    
    with st.container(border=True):
        c_date, c_court = st.columns(2)
        with c_date: date = st.date_input("日期", datetime.now())
        with c_court:
            court_units = st.number_input("場地單位 ($250/位)", min_value=1, value=2)
            calc_court_fee = court_units * 250
            st.caption(f"🏟️ 場地費：${calc_court_fee}")

        st.write("#### 💰 收入人數")
        i1, i2, i3 = st.columns(3)
        with i1: p140 = st.number_input("$140", min_value=0, step=1, key="a140")
        with i2: p180 = st.number_input("$180", min_value=0, step=1, key="a180")
        with i3: p240 = st.number_input("$240", min_value=0, step=1, key="a240")
        auto_income = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 總收入：**${auto_income}**")

        st.write("#### 🎾 用球明細")
        ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []
        
        if not ball_options:
            st.warning("⚠️ 請先在『球種設定』新增球種資料")
        else:
            total_ball_cost = 0.0
            ball_details_text = []
            for index, usage in enumerate(st.session_state.ball_usage):
                uid = usage.get("id", str(time.time() + index))
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    cur = usage.get('ball_type', "")
                    idx = ball_options.index(cur) if cur in ball_options else 0
                    usage['ball_type'] = st.selectbox("球種", ball_options, index=idx, key=f"at_{uid}", label_visibility="collapsed")
                with r2:
                    usage['count'] = st.number_input("顆數", min_value=0, step=1, value=usage.get('count', 0), key=f"an_{uid}", label_visibility="collapsed")
                with r3:
                    if st.button("❌", key=f"ad_{uid}"):
                        st.session_state.ball_usage.pop(index)
                        st.rerun()
                
                u_p = float(settings_df.loc[settings_df["球種"] == usage['ball_type'], "單價"].values[0])
                total_ball_cost += u_p * usage['count']
                if usage['count'] > 0: ball_details_text.append(f"{usage['ball_type']}x{usage['count']}")
            
            if st.button("➕ 新增球種項目"):
                st.session_state.ball_usage.append({"id": str(time.time()), "ball_type": ball_options[0], "count": 0})
                st.rerun()

            total_cost = calc_court_fee + total_ball_cost
            profit = auto_income - total_cost
            st.write("---")
            if st.button("🚀 儲存紀錄", use_container_width=True):
                new_row = pd.DataFrame([[str(date), int(calc_court_fee), ", ".join(ball_details_text), round(total_ball_cost, 1), int(auto_income), round(profit, 1)]], columns=COL_RECORDS)
                conn.update(worksheet="Records", data=pd.concat([records_df, new_row], ignore_index=True))
                st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": ball_options[0], "count": 0}]
                st.success("✅ 儲存成功")
                st.rerun()

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種管理")
    st.dataframe(settings_df, use_container_width=True)
    with st.form("new_ball"):
        n_name = st.text_input("球種名稱")
        n_price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存球種"):
            if n_name and n_price > 0:
                new_entry = pd.DataFrame([[n_name, n_price, round(n_price/12, 2)]], columns=COL_SETTINGS)
                s_df_clean = settings_df[settings_df["球種"] != n_name] if not settings_df.empty else settings_df
                conn.update(worksheet="Settings", data=pd.concat([s_df_clean, new_entry], ignore_index=True))
                st.rerun()

# --- TAB 3: 歷史紀錄與編輯 ---
with tab3:
    if not records_df.empty:
        df_display = records_df.copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display.sort_index(ascending=False), use_container_width=True)

        st.divider()
        st.subheader("✏️ 編輯 / 🗑️ 刪除")
        edit_idx = st.number_input("輸入紀錄編號", min_value=1, max_value=len(records_df), step=1)
        
        # 使用 .iloc[] 按位置取值，避免欄位名稱對不上的問題
        old_row = records_df.iloc[edit_idx - 1]
        
        with st.expander(f"修改第 {edit_idx} 筆資料"):
            with st.form("edit_form"):
                try:
                    d_val = datetime.strptime(str(old_row[0]), '%Y-%m-%d')
                except:
                    d_val = datetime.now()
                
                e_date = st.date_input("日期", d_val)
                e_court = st.number_input("場地費", value=int(old_row[1]))
                e_detail = st.text_input("球種明細", value=str(old_row[2]))
                e_ball_cost = st.number_input("用球總成本", value=float(old_row[3]))
                e_income = st.number_input("總收入", value=int(old_row[4]))
                e_profit = e_income - (e_court + e_ball_cost)
                
                c1, c2 = st.columns(2)
                with c1: save = st.form_submit_button("💾 儲存修改")
                with c2: delete = st.form_submit_button("🗑️ 刪除紀錄")

            if save:
                records_df.iloc[edit_idx - 1] = [str(e_date), e_court, e_detail, e_ball_cost, e_income, e_profit]
                conn.update(worksheet="Records", data=records_df)
                st.success("更新成功！")
                st.rerun()
            
            if delete:
                updated_df = records_df.drop(records_df.index[edit_idx - 1])
                conn.update(worksheet="Records", data=updated_df)
                st.rerun()
