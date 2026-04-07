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

st.title("🏸 羽球團務管理系統 (多球種版)")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 (支援多球種) ---
with tab1:
    st.subheader("新增開團資訊")
    
    # 建立一個 Session State 來存儲本次開團使用的球種列表
    if 'ball_usage' not in st.session_state:
        st.session_state.ball_usage = [{"ball_type": "", "count": 0}]

    with st.container(border=True):
        col_date, col_court = st.columns(2)
        with col_date:
            date = st.date_input("開團日期", datetime.now())
        with col_court:
            court_fee = st.number_input("本場場地費", value=500, step=50)

        st.write("---")
        st.write("#### 🎾 用球明細")
        
        total_ball_cost = 0.0
        ball_details_text = []

        # 動態顯示多個球種輸入框
        ball_options = settings_df["球種"].tolist() if not settings_df.empty else []
        
        if not ball_options:
            st.warning("請先到『球種設定』新增球種")
        else:
            for i, usage in enumerate(st.session_state.ball_usage):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    usage['ball_type'] = st.selectbox(f"球種 {i+1}", ball_options, key=f"type_{i}")
                with c2:
                    usage['count'] = st.number_input(f"數量 (顆)", min_value=0, step=1, key=f"count_{i}")
                with c3:
                    if st.button("❌", key=f"del_{i}"):
                        st.session_state.ball_usage.pop(i)
                        st.rerun()
                
                # 計算單個球種成本
                u_price = float(settings_df.loc[settings_df["球種"] == usage['ball_type'], "單價"].values[0])
                total_ball_cost += u_price * usage['count']
                if usage['count'] > 0:
                    ball_details_text.append(f"{usage['ball_type']}x{usage['count']}")

            if st.button("➕ 新增另一個球種"):
                st.session_state.ball_usage.append({"ball_type": ball_options[0], "count": 0})
                st.rerun()

        st.write("---")
        income = st.number_input("本團總收入 (報名費)", value=1200, step=100)
        
        # 最終計算
        total_cost = court_fee + total_ball_cost
        profit = income - total_cost

        # 儀表板
        m1, m2, m3 = st.columns(3)
        m1.metric("用球總額", f"${total_ball_cost:.1f}")
        m2.metric("總支出", f"${total_cost:.1f}")
        m3.metric("淨利", f"${profit:.1f}", delta=f"{profit:.1f}")

        if st.button("🚀 儲存本次紀錄"):
            if not ball_details_text:
                st.error("請至少輸入一個球種的消耗數量")
            else:
                new_row = pd.DataFrame([{
                    "日期": str(date),
                    "場地費": court_fee,
                    "球種明細": ", ".join(ball_details_text),
                    "用球總成本": round(total_ball_cost, 1),
                    "總收入": income,
                    "淨利": round(profit, 1)
                }])
                conn.update(worksheet="Records", data=pd.concat([records_df, new_row], ignore_index=True))
                # 儲存後重置
                st.session_state.ball_usage = [{"ball_type": "", "count": 0}]
                st.balloons()
                st.success("存檔成功！")
                st.rerun()

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單管理")
    if not settings_df.empty:
        st.dataframe(settings_df, use_container_width=True)
        del_ball = st.selectbox("選擇要刪除的球種", ["請選擇..."] + settings_df["球種"].tolist())
        if st.button("🗑️ 刪除選中球種"):
            if del_ball != "請選擇...":
                new_settings = settings_df[settings_df["球種"] != del_ball]
                conn.update(worksheet="Settings", data=new_settings)
                st.rerun()
    
    st.divider()
    with st.form("add_ball"):
        n_name = st.text_input("新增球種名稱")
        n_price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存"):
            if n_name and n_price > 0:
                u_p = round(n_price / 12, 2)
                new_entry = pd.DataFrame([{"球種": n_name, "單筒價格": n_price, "單價": u_p}])
                s_df_clean = settings_df[settings_df["球種"] != n_name] if not settings_df.empty else settings_df
                conn.update(worksheet="Settings", data=pd.concat([s_df_clean, new_entry], ignore_index=True))
                st.rerun()

# --- TAB 3: 歷史紀錄 ---
with tab3:
    st.subheader("📜 歷史開團紀錄")
    if not records_df.empty:
        # 重設索引以便刪除
        display_df = records_df.copy()
        display_df.index = range(1, len(display_df) + 1)
        st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
        
        del_idx = st.number_input("輸入要刪除的列號", min_value=1, max_value=len(records_df), step=1)
        if st.button("🗑️ 刪除該筆紀錄"):
            new_records = records_df.drop(records_df.index[del_idx - 1])
            conn.update(worksheet="Records", data=new_records)
            st.rerun()
    else:
        st.write("目前尚無資料")
