import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 頁面配置 ---
st.set_page_config(page_title="羽球管家 Pro", layout="wide")

# 美化 UI
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { 
        background-color: #1f2937; 
        padding: 15px; 
        border-radius: 15px; 
        border: 1px solid #4ade80; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 建立連線 (強制即時更新模式) ---
try:
    # 這裡的 ttl=0 非常重要，確保每次操作都抓取最新資料
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    st.sidebar.success("✅ Google Sheets 已連線")
except Exception as e:
    st.sidebar.error(f"❌ 連線失敗: {e}")
    st.stop()

# --- 3. 資料讀取函數 (加入內容檢查) ---
def load_all_data():
    # 讀取 Settings (球種設定)
    try:
        s_df = conn.read(worksheet="Settings", ttl=0).dropna(how="all")
    except:
        s_df = pd.DataFrame(columns=["球種", "單筒價格", "單價"])
    
    # 讀取 Records (開團紀錄)
    try:
        r_df = conn.read(worksheet="Records", ttl=0).dropna(how="all")
    except:
        r_df = pd.DataFrame(columns=["日期", "場地費", "球種", "球單價", "用球小計", "收入", "成本", "利潤"])
    
    return s_df, r_df

# 初始化資料
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
            
            # 從設定檔抓取可用球種
            if not settings_df.empty and "球種" in settings_df.columns:
                ball_options = settings_df["球種"].unique().tolist()
            else:
                ball_options = []
            
            if not ball_options:
                st.warning("⚠️ 請先前往『球種設定』新增球種")
                selected_ball = None
                current_unit_price = 0.0
            else:
                selected_ball = st.selectbox("選擇球種", ball_options)
                # 抓取對應單價
                price_row = settings_df.loc[settings_df["球種"] == selected_ball]
                current_unit_price = float(price_row["單價"].values[0]) if not price_row.empty else 0.0
            
            st.info(f"💡 目前球單價：${current_unit_price:.2f}")

        with c2:
            ball_count = st.number_input("消耗球數 (顆)", value=0, step=1)
            income = st.number_input("本團總收入", value=1200, step=100)

        # 自動計算
        ball_subtotal = round(ball_count * current_unit_price, 1)
        total_cost = round(court_fee + ball_subtotal, 1)
        profit = round(income - total_cost, 1)

        submit_record = st.form_submit_button("🚀 儲存紀錄")

    if submit_record:
        if selected_ball:
            new_record = pd.DataFrame([{
                "日期": date.strftime('%Y-%m-%d'), 
                "場地費": court_fee, 
                "球種": selected_ball,
                "球單價": current_unit_price, 
                "用球小計": ball_subtotal,
                "收入": income, 
                "成本": total_cost, 
                "利潤": profit
            }])
            # 寫入更新
            try:
                updated_r = pd.concat([records_df, new_record], ignore_index=True)
                conn.update(worksheet="Records", data=updated_r)
                st.balloons()
                st.success("開團紀錄已存入 Google Sheets！")
                st.rerun()
            except Exception as e:
                st.error(f"存檔出錯：{e}")
        else:
            st.error("請填寫完整資訊")

    # 即時顯示數據
    m1, m2, m3 = st.columns(3)
    m1.metric("用球小計", f"${ball_subtotal}")
    m2.metric("總成本", f"${total_cost}")
    m3.metric("本團利潤", f"${profit}")

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單管理")
    if not settings_df.empty:
        st.dataframe(settings_df, use_container_width=True)
    else:
        st.write("目前無球種資料")
    
    st.divider()
    with st.form("settings_form"):
        st.write("### ➕ 新增/更新球價")
        new_name = st.text_input("球種名稱 (例如: RSL No.4)")
        new_tube = st.number_input("單筒價格", value=0.0, step=10.0)
        submit_s = st.form_submit_button("✅ 儲存球種")
    
    if submit_s:
        if new_name and new_tube > 0:
            unit_p = round(new_tube / 12, 2) # 自動計算單價 (單筒/12)
            new_ball = pd.DataFrame([{"球種": new_name, "單筒價格": new_tube, "單價": unit_p}])
            
            # 覆蓋舊資料邏輯
            if not settings_df.empty and new_name in settings_df["球種"].values:
                settings_df = settings_df[settings_df["球種"] != new_name]
            
            try:
                updated_s = pd.concat([settings_df, new_ball], ignore_index=True)
                conn.update(worksheet="Settings", data=updated_s)
                st.success(f"已儲存 {new_name}，單價為 ${unit_p}")
                st.rerun()
            except Exception as e:
                st.error(f"更新失敗：{e}")

# --- TAB 3: 歷史紀錄 ---
with tab3:
    st.subheader("📜 歷史紀錄 (由新到舊)")
    if not records_df.empty:
        # 確保日期格式正確排序
        records_df['日期'] = pd.to_datetime(records_df['日期']).dt.date
        st.dataframe(records_df.sort_values("日期", ascending=False), use_container_width=True)
        
        total_profit = records_df["利潤"].sum()
        st.divider()
        st.metric("累計總盈餘", f"${total_profit:,.1f}")
    else:
        st.write("尚無歷史開團紀錄")
