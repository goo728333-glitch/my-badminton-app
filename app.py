import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 頁面配置與美化 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #1f2937; 
        padding: 15px; 
        border-radius: 15px; 
        border: 1px solid #4ade80; 
    }
    .stTabs [data-baseweb="tab"] { font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 (使用 ttl=0 確保資料不被快取，即時更新) ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 讀取設定檔與紀錄 (若讀不到則建立空表)
def get_data():
    try:
        s_df = conn.read(worksheet="Settings")
    except:
        s_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])
    
    try:
        r_df = conn.read(worksheet="Records")
    except:
        r_df = pd.DataFrame(columns=["日期", "場地費", "球種", "球單價", "用球小計", "收入", "成本", "利潤"])
    return s_df, r_df

settings_df, records_df = get_data()

st.title("🏸 羽球團務管理系統")

tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄"])

# --- TAB 1: 新增開團 ---
with tab1:
    with st.form("record_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input("開團日期", datetime.now())
            court_fee = st.number_input("場地費", value=500, step=50)
            
            # 從試算表抓取球種清單
            ball_options = settings_df["球種"].tolist() if not settings_df.empty else []
            if not ball_options:
                st.warning("⚠️ 請先到『球種設定』分頁新增球種！")
                selected_ball = None
                current_unit_price = 0.0
            else:
                selected_ball = st.selectbox("選擇球種", ball_options)
                current_unit_price = settings_df.loc[settings_df["球種"] == selected_ball, "單價"].values[0]
            
            st.info(f"💡 目前球單價：${current_unit_price:.1f} / 顆")

        with c2:
            ball_count = st.number_input("消耗球數 (顆)", value=0, step=1)
            income = st.number_input("本團總收入 (報名費總額)", value=1200, step=100)

        # 自動計算
        ball_subtotal = round(ball_count * current_unit_price, 1)
        total_cost = round(court_fee + ball_subtotal, 1)
        profit = round(income - total_cost, 1)

        submit_record = st.form_submit_button("🚀 儲存本次紀錄")

    if submit_record:
        if not selected_ball:
            st.error("錯誤：沒有選擇球種，無法存檔。")
        else:
            new_record = pd.DataFrame([{
                "日期": str(date), "場地費": court_fee, "球種": selected_ball,
                "球單價": current_unit_price, "用球小計": ball_subtotal,
                "收入": income, "成本": total_cost, "利潤": profit
            }])
            # 寫入 Records 分頁
            updated_r = pd.concat([records_df, new_record], ignore_index=True)
            conn.update(worksheet="Records", data=updated_r)
            st.balloons()
            st.success(f"存檔成功！今日利潤：${profit}")
            st.rerun()

    # 儀表板
    m1, m2, m3 = st.columns(3)
    m1.metric("用球小計", f"${ball_subtotal}")
    m2.metric("總成本", f"${total_cost}")
    m3.metric("本團利潤", f"${profit}", delta=f"{profit}")

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單與價格管理")
    st.dataframe(settings_df, use_container_width=True)
    
    st.divider()
    st.write("### ➕ 新增或更新球種")
    with st.form("settings_form"):
        new_ball_name = st.text_input("球種名稱 (例如: RSL No.4)")
        new_tube_price = st.number_input("單筒價格 (自動除以12算出單價)", value=0.0, step=10.0)
        
        submit_settings = st.form_submit_button("✅ 確認新增/更新")
    
    if submit_settings:
        if new_ball_name and new_tube_price > 0:
            unit_p = round(new_tube_price / 12, 2)
            new_entry = pd.DataFrame([{"球種": new_ball_name, "單筒價格": new_tube_price, "單價": unit_p}])
            
            # 若球種已存在則更新，不存在則新增
            if not settings_df.empty and new_ball_name in settings_df["球種"].values:
                settings_df = settings_df[settings_df["球種"] != new_ball_name]
            
            updated_s = pd.concat([settings_df, new_entry], ignore_index=True)
            conn.update(worksheet="Settings", data=updated_s)
            st.success(f"已儲存 {new_ball_name}，每顆單價為 ${unit_p}")
            st.rerun()
        else:
            st.error("請填寫完整的球種名稱與單筒價格")

# --- TAB 3: 歷史紀錄 ---
with tab3:
    st.subheader("📜 歷史開團紀錄")
    if not records_df.empty:
        st.dataframe(records_df.sort_values("日期", ascending=False), use_container_width=True)
        
        # 簡單統計
        total_all_profit = records_df["利潤"].sum()
        st.write(f"### 📈 累計總利潤： :green[${total_all_profit:,.1f}]")
    else:
        st.write("目前尚無開團紀錄。")
