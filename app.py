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

# --- 2. 建立連線與強制重整功能 ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if st.sidebar.button("🔄 重新載入雲端資料"):
    st.cache_data.clear()
    st.rerun()

# --- 3. 強化版資料讀取 (含自動重試) ---
def load_data_with_retry(worksheet_name, expected_cols):
    # 最多嘗試 3 次
    for i in range(3):
        try:
            df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
            if not df.empty:
                return df
        except:
            time.sleep(1) # 失敗就等一秒再試
    return pd.DataFrame(columns=expected_cols)

settings_df = load_data_with_retry("Settings", ["球種", "單筒價格", "單價"])
records_df = load_data_with_retry("Records", ["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"])

st.title("🏸 羽球管家")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 ---
with tab1:
    # 建立 Session State 避免畫面重置時資料消失
    if 'ball_usage' not in st.session_state:
        st.session_state.ball_usage = [{"ball_type": "", "count": 0}]

    with st.container(border=True):
        c_date, c_court = st.columns(2)
        with c_date:
            date = st.date_input("日期", datetime.now())
        with c_court:
            court_units = st.number_input("場地單位 ($250/位)", min_value=1, value=2)
            calc_court_fee = court_units * 250
            st.caption(f"🏟️ 場地費：${calc_court_fee}")

        st.write("---")
        st.write("#### 💰 收入人數")
        i_col1, i_col2, i_col3 = st.columns(3)
        with i_col1: p140 = st.number_input("$140", min_value=0, step=1)
        with i_col2: p180 = st.number_input("$180", min_value=0, step=1)
        with i_col3: p240 = st.number_input("$240", min_value=0, step=1)
        
        auto_income = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 目前總收入：**${auto_income}**")

        st.write("---")
        st.write("#### 🎾 用球明細")
        
        ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []
        
        if not ball_options:
            st.error("❌ 雲端抓不到球種！請檢查 Google 試算表或按左側『重新載入』")
        else:
            total_ball_cost = 0.0
            ball_details_text = []
            
            for i, usage in enumerate(st.session_state.ball_usage):
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    # 確保預設值在選單內
                    d_val = usage['ball_type'] if usage['ball_type'] in ball_options else ball_options[0]
                    usage['ball_type'] = st.selectbox(f"球種", ball_options, index=ball_options.index(d_val), key=f"t_{i}", label_visibility="collapsed")
                with r2:
                    usage['count'] = st.number_input(f"顆數", min_value=0, step=1, key=f"n_{i}", label_visibility="collapsed")
                with r3:
                    if st.button("❌", key=f"d_{i}"):
                        st.session_state.ball_usage.pop(i)
                        st.rerun()
                
                # 即時計算成本
                u_p = float(settings_df.loc[settings_df["球種"] == usage['ball_type'], "單價"].values[0])
                total_ball_cost += u_p * usage['count']
                if usage['count'] > 0:
                    ball_details_text.append(f"{usage['ball_type']}x{usage['count']}")

            if st.button("➕ 新增球種項目"):
                st.session_state.ball_usage.append({"ball_type": ball_options[0], "count": 0})
                st.rerun()

            st.write("---")
            total_cost = calc_court_fee + total_ball_cost
            profit = auto_income - total_cost

            m1, m2, m3 = st.columns(3)
            m1.metric("球費", f"${total_ball_cost:.1f}")
            m2.metric("總支", f"${total_cost:.1f}")
            m3.metric("利潤", f"${profit:.1f}")

            if st.button("🚀 儲存紀錄", use_container_width=True):
                new_row = pd.DataFrame([{"日期": str(date), "場地費": calc_court_fee, "球種明細": ", ".join(ball_details_text), "用球總成本": round(total_ball_cost, 1), "總收入": auto_income, "淨利": round(profit, 1)}])
                conn.update(worksheet="Records", data=pd.concat([records_df, new_row], ignore_index=True))
                st.session_state.ball_usage = [{"ball_type": ball_options[0], "count": 0}]
                st.success("✅ 儲存成功！")
                st.rerun()

# --- TAB 2 & 3 保持不變 ---
with tab2:
    st.subheader("🛠 球種管理")
    st.dataframe(settings_df, use_container_width=True)
    with st.form("add_ball"):
        n_name = st.text_input("球種名稱")
        n_price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存球種"):
            if n_name and n_price > 0:
                u_p = round(n_price / 12, 2)
                new_entry = pd.DataFrame([{"球種": n_name, "單筒價格": n_price, "單價": u_p}])
                s_df_clean = settings_df[settings_df["球種"] != n_name] if not settings_df.empty else settings_df
                conn.update(worksheet="Settings", data=pd.concat([s_df_clean, new_entry], ignore_index=True))
                st.rerun()

with tab3:
    st.subheader("📜 歷史紀錄")
    if not records_df.empty:
        df_show = records_df.copy()
        df_show.index = range(1, len(df_show) + 1)
        st.dataframe(df_show.sort_index(ascending=False), use_container_width=True)
        idx = st.number_input("輸入列號刪除", min_value=1, max_value=len(records_df), step=1)
        if st.button("🗑️ 刪除紀錄"):
            conn.update(worksheet="Records", data=records_df.drop(records_df.index[idx - 1]))
            st.rerun()
