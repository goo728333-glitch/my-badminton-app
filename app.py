import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 頁面配置 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #1f2937; padding: 10px; border-radius: 12px; border: 1px solid #4ade80; 
    }
    .stNumberInput input { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    # 在側邊欄放一個手動重整按鈕，抓不到時點一下
    if st.sidebar.button("🔄 強制重整資料"):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.success("✅ 已連線")
except Exception as e:
    st.sidebar.error(f"❌ 連線失敗: {e}")
    st.stop()

# --- 3. 穩定讀取函數 ---
def load_all_data():
    # 讀取 Settings
    try:
        s_df = conn.read(worksheet="Settings", ttl=0).dropna(how="all")
    except Exception:
        s_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])
    
    # 讀取 Records
    try:
        r_df = conn.read(worksheet="Records", ttl=0).dropna(how="all")
    except Exception:
        r_df = pd.DataFrame(columns=["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"])
    return s_df, r_df

# 載入資料
settings_df, records_df = load_all_data()

st.title("🏸 羽球管家")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 ---
with tab1:
    # 檢查是否有球種資料，若無則顯示警告
    if settings_df.empty:
        st.warning("⚠️ 目前抓不到球種資料，請確認 Google 試算表是否有內容，或點擊左側『強制重整』")
    
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
        with i_col1: p140 = st.number_input("$140", min_value=0, step=1, key="in140")
        with i_col2: p180 = st.number_input("$180", min_value=0, step=1, key="in180")
        with i_col3: p240 = st.number_input("$240", min_value=0, step=1, key="in240")
        
        auto_income = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 總收入：**${auto_income}**")

        st.write("---")
        st.write("#### 🎾 用球明細")
        
        total_ball_cost = 0.0
        ball_details_text = []
        ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []
        
        if not ball_options:
            st.error("❌ 找不到可用球種，請先到『球種設定』確認。")
        else:
            for i, usage in enumerate(st.session_state.ball_usage):
                row_c1, row_c2, row_c3 = st.columns([5, 4, 1.5])
                with row_c1:
                    # 避免選擇到不存在的球種
                    default_type = usage['ball_type'] if usage['ball_type'] in ball_options else ball_options[0]
                    usage['ball_type'] = st.selectbox(f"球種", ball_options, index=ball_options.index(default_type), key=f"t_{i}", label_visibility="collapsed")
                with row_c2:
                    usage['count'] = st.number_input(f"顆數", min_value=0, step=1, key=f"n_{i}", label_visibility="collapsed")
                with row_c3:
                    if st.button("❌", key=f"d_{i}"):
                        st.session_state.ball_usage.pop(i)
                        st.rerun()
                
                # 計算成本
                price_data = settings_df.loc[settings_df["球種"] == usage['ball_type'], "單價"]
                u_price = float(price_data.values[0]) if not price_data.empty else 0.0
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
                st.session_state.ball_usage = [{"ball_type": ball_options[0] if ball_options else "", "count": 0}]
                st.success("✅ 儲存成功！")
                st.rerun()

# --- TAB 2 & 3 ---
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
