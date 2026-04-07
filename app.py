import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 頁面配置與美化 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1f2937; padding: 15px; border-radius: 15px; border: 1px solid #4ade80; }
    </style>
    """, unsafe_allow_html=True)

# --- 建立 Google Sheets 連線 ---
# 注意：正式部署時，需在 Streamlit Cloud 的 Secrets 設定中放入試算表網址
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取現有的球種設定 (Settings 分頁)
try:
    settings_df = conn.read(worksheet="Settings")
except:
    settings_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])

st.title("🏸 羽球團務管理系統")

tab1, tab2 = st.tabs(["📝 新增開團", "⚙️ 球種設定"])

# --- TAB 1: 新增開團 ---
with tab1:
    with st.form("record_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("開團日期", datetime.now())
            court_fee = st.number_input("場地費", value=500, step=50)
            
            # 從試算表動態抓取球種
            ball_options = settings_df["球種"].tolist() if not settings_df.empty else ["請先至設定新增球種"]
            selected_ball = st.selectbox("選擇球種", ball_options)
            
            # 自動帶出單價
            if not settings_df.empty and selected_ball in ball_options:
                current_unit_price = settings_df.loc[settings_df["球種"] == selected_ball, "單價"].values[0]
            else:
                current_unit_price = 0.0
            st.info(f"當前球單價：${current_unit_price:.1f}")

        with c2:
            ball_count = st.number_input("消耗球數 (顆)", value=0, step=1)
            income = st.number_input("本團總收入", value=1200, step=100)

        ball_subtotal = ball_count * current_unit_price
        total_cost = court_fee + ball_subtotal
        profit = income - total_cost

        if st.form_submit_button("🚀 儲存並同步至 Google 表格"):
            # 準備存入 Records 分頁的資料
            new_record = pd.DataFrame([{
                "日期": str(date), "場地費": court_fee, "球種": selected_ball,
                "球單價": current_unit_price, "用球小計": ball_subtotal,
                "收入": income, "成本": total_cost, "利潤": profit
            }])
            # 讀取舊資料並合併
            existing_records = conn.read(worksheet="Records")
            updated_records = pd.concat([existing_records, new_record], ignore_index=True)
            conn.update(worksheet="Records", data=updated_records)
            st.balloons()
            st.success("資料已成功寫入 Google 試算表！")

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單管理")
    st.dataframe(settings_df, use_container_width=True)
    
    st.divider()
    with st.form("settings_form"):
        new_name = st.text_input("新增球種名稱")
        new_tube_price = st.number_input("單筒價格", value=0.0)
        
        if st.form_submit_button("確認新增"):
            if new_name and new_tube_price > 0:
                unit_p = round(new_tube_price / 12, 2) # 自動計算 (單筒/12)
                new_ball_data = pd.DataFrame([{"球種": new_name, "單筒價格": new_tube_price, "單價": unit_p}])
                updated_settings = pd.concat([settings_df, new_ball_data], ignore_index=True)
                conn.update(worksheet="Settings", data=updated_settings)
                st.success(f"已新增 {new_name}")
                st.rerun()
