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
        background-color: #1f2937; padding: 15px; border-radius: 15px; border: 1px solid #4ade80; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    st.sidebar.success("✅ Google Sheets 已連線")
except Exception as e:
    st.sidebar.error(f"❌ 連線失敗: {e}")
    st.stop()

# --- 3. 資料讀取函數 ---
def load_all_data():
    try:
        s_df = conn.read(worksheet="Settings", ttl=0).dropna(how="all")
    except:
        s_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])
    
    try:
        r_df = conn.read(worksheet="Records", ttl=0).dropna(how="all")
    except:
        r_df = pd.DataFrame(columns=["日期", "場地費", "球種", "球單價", "用球小計", "收入", "成本", "利潤"])
    return s_df, r_df

settings_df, records_df = load_all_data()

st.title("🏸 羽球團務管理系統")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 ---
with tab1:
    with st.form("record_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("開團日期", datetime.now())
            court_fee = st.number_input("場地費", value=500, step=50)
            ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []
            if not ball_options:
                st.warning("⚠️ 請先新增球種")
                selected_ball = None
                current_unit_price = 0.0
            else:
                selected_ball = st.selectbox("選擇球種", ball_options)
                current_unit_price = float(settings_df.loc[settings_df["球種"] == selected_ball, "單價"].values[0])
            st.info(f"💡 目前球單價：${current_unit_price:.2f}")
        with c2:
            ball_count = st.number_input("消耗球數 (顆)", value=0, step=1)
            income = st.number_input("本團總收入", value=1200, step=100)

        ball_subtotal = round(ball_count * current_unit_price, 1)
        total_cost = round(court_fee + ball_subtotal, 1)
        profit = round(income - total_cost, 1)
        if st.form_submit_button("🚀 儲存紀錄"):
            if selected_ball:
                new_record = pd.DataFrame([{"日期": str(date), "場地費": court_fee, "球種": selected_ball, "球單價": current_unit_price, "用球小計": ball_subtotal, "收入": income, "成本": total_cost, "利潤": profit}])
                conn.update(worksheet="Records", data=pd.concat([records_df, new_record], ignore_index=True))
                st.rerun()

# --- TAB 2: 球種設定 (含刪除功能) ---
with tab2:
    st.subheader("🛠 球種管理")
    if not settings_df.empty:
        # 顯示表格
        st.dataframe(settings_df, use_container_width=True)
        # 刪除選擇器
        del_ball = st.selectbox("選擇要刪除的球種", ["請選擇..."] + settings_df["球種"].tolist())
        if st.button("🗑️ 刪除選中球種"):
            if del_ball != "請選擇...":
                new_settings = settings_df[settings_df["球種"] != del_ball]
                conn.update(worksheet="Settings", data=new_settings)
                st.success(f"已刪除 {del_ball}")
                st.rerun()
    
    st.divider()
    with st.form("add_ball"):
        st.write("### ➕ 新增/更新球種")
        n_name = st.text_input("球種名稱")
        n_price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存"):
            if n_name and n_price > 0:
                u_p = round(n_price / 12, 2)
                new_entry = pd.DataFrame([{"球種": n_name, "單筒價格": n_price, "單價": u_p}])
                # 更新邏輯
                s_df_clean = settings_df[settings_df["球種"] != n_name] if not settings_df.empty else settings_df
                conn.update(worksheet="Settings", data=pd.concat([s_df_clean, new_entry], ignore_index=True))
                st.rerun()

# --- TAB 3: 歷史紀錄 (含刪除功能) ---
with tab3:
    st.subheader("📜 歷史紀錄")
    if not records_df.empty:
        # 給每一行加上索引編號以便刪除
        display_df = records_df.copy()
        display_df.index = range(1, len(display_df) + 1)
        st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
        
        # 刪除紀錄
        del_idx = st.number_input("輸入要刪除的列號 (Index)", min_value=1, max_value=len(records_df), step=1)
        if st.button("🗑️ 刪除該筆開團紀錄"):
            # 因為 dataframe 顯示是 1-based，所以要減 1
            new_records = records_df.drop(records_df.index[del_idx - 1])
            conn.update(worksheet="Records", data=new_records)
            st.success(f"第 {del_idx} 筆紀錄已刪除")
            st.rerun()
    else:
        st.write("目前尚無紀錄")
