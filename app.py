import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 頁面配置 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")

# CSS 優化：針對手機螢幕調整間距與字體
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #1f2937; padding: 10px; border-radius: 12px; border: 1px solid #4ade80; 
    }
    /* 讓手機上的輸入框更緊湊 */
    .stNumberInput input { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    st.sidebar.success("✅ 已連線")
except Exception as e:
    st.sidebar.error(f"❌ 連線失敗: {e}")
    st.stop()

# --- 3. 資料讀取 ---
def load_all_data():
    try:
        s_df = conn.read(worksheet="Settings", ttl=0).dropna(how="all")
    except:
        s_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])
    try:
        r_df = conn.read(worksheet="Records", ttl=0).dropna(how="all")
    except:
        r_df = pd.DataFrame(columns=["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"])
    return s_df, r_df

settings_df, records_df = load_all_data()

st.title("🏸 羽球管家")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 ---
with tab1:
    if 'ball_usage' not in st.session_state:
        st.session_state.ball_usage = [{"ball_type": "", "count": 0}]

    with st.container(border=True):
        c_date, c_court = st.columns(2)
        with c_date:
            date = st.date_input("日期", datetime.now())
        with c_court:
            court_units = st.number_input("場地單位 ($250/位)", min_value=1, value=2, step=1)
            calc_court_fee = court_units * 250
            st.caption(f"🏟️ 場地費：${calc_court_fee}")

        st.write("---")
        st.write("#### 💰 收入人數")
        i_col1, i_col2, i_col3 = st.columns(3)
        with i_col1: p140 = st.number_input("$140", min_value=0, step=1)
        with i_col2: p180 = st.number_input("$180", min_value=0, step=1)
        with i_col3: p240 = st.number_input("$240", min_value=0, step=1)
        
        auto_income = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 總收入：**${auto_income}**")

        st.write("---")
        st.write("#### 🎾 用球明細")
        
        total_ball_cost = 0.0
        ball_details_text = []
        ball_options = settings_df["球種"].tolist() if not settings_df.empty else []
        
        if not ball_options:
            st.warning("請先新增球種")
        else:
            # 使用 loop 產生球種輸入列
            for i, usage in enumerate(st.session_state.ball_usage):
                # 調整比例 [5, 4, 1.5] 讓中間的數字框更大
                row_c1, row_c2, row_c3 = st.columns([5, 4, 1.5])
                with row_c1:
                    usage['ball_type'] = st.selectbox(f"球種", ball_options, key=f"t_{i}", label_visibility="collapsed")
                with row_c2:
                    usage['count'] = st.number_input(f"顆數", min_value=0, step=1, key=f"n_{i}", label_visibility="collapsed")
                with row_c3:
                    if st.button("❌", key=f"d_{i}"):
                        st.session_state.ball_usage.pop(i)
                        st.rerun()
                
                u_price = float(settings_df.loc[settings_df["球種"] == usage['ball_type'], "單價"].values[0])
                total_ball_cost += u_price * usage['count']
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
            if not ball_details_text and auto_income == 0:
                st.error("請輸入內容")
            else:
                new_row = pd.DataFrame([{"日期": str(date), "場地費": calc_court_fee, "球種明細": ", ".join(ball_details_text), "用球總成本": round(total_ball_cost, 1), "總收入": auto_income, "淨利": round(profit, 1)}])
                conn.update(worksheet="Records", data=pd.concat([records_df, new_row], ignore_index=True))
                st.session_state.ball_usage = [{"ball_type": ball_options[0], "count": 0}]
                st.success("已儲存！")
                st.rerun()

# --- TAB 2 & 3 保持邏輯 ---
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
            
