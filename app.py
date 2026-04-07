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
        return df if not df.empty else pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

settings_df = load_data_stable("Settings", ["球種", "單筒價格", "單價"])
records_df = load_data_stable("Records", ["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"])

st.title("🏸 羽球管家 Pro")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄 / 編輯"])

# --- TAB 1: 新增開團 (保持穩定版邏輯) ---
with tab1:
    if 'ball_usage' not in st.session_state or not isinstance(st.session_state.ball_usage, list):
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
        with i1: p140 = st.number_input("$140", min_value=0, step=1, key="add_140")
        with i2: p180 = st.number_input("$180", min_value=0, step=1, key="add_180")
        with i3: p240 = st.number_input("$240", min_value=0, step=1, key="add_240")
        auto_income = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 總收入：**${auto_income}**")

        st.write("#### 🎾 用球明細")
        ball_options = settings_df["球種"].unique().tolist() if not settings_df.empty else []
        
        if ball_options:
            total_ball_cost = 0.0
            ball_details_text = []
            for index, usage in enumerate(st.session_state.ball_usage):
                uid = usage.get("id", str(time.time()))
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    cur = usage.get('ball_type', "")
                    idx = ball_options.index(cur) if cur in ball_options else 0
                    usage['ball_type'] = st.selectbox("球種", ball_options, index=idx, key=f"add_t_{uid}", label_visibility="collapsed")
                with r2:
                    usage['count'] = st.number_input("顆數", min_value=0, step=1, value=usage.get('count', 0), key=f"add_n_{uid}", label_visibility="collapsed")
                with r3:
                    if st.button("❌", key=f"add_d_{uid}"):
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
                new_row = pd.DataFrame([{"日期": str(date), "場地費": calc_court_fee, "球種明細": ", ".join(ball_details_text), "用球總成本": round(total_ball_cost, 1), "總收入": auto_income, "淨利": round(profit, 1)}])
                conn.update(worksheet="Records", data=pd.concat([records_df, new_row], ignore_index=True))
                st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": ball_options[0], "count": 0}]
                st.success("✅ 儲存成功")
                st.rerun()

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單")
    st.dataframe(settings_df, use_container_width=True)
    with st.form("new_ball"):
        n_name = st.text_input("球種名稱")
        n_price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存"):
            if n_name and n_price > 0:
                u_p = round(n_price / 12, 2)
                new_entry = pd.DataFrame([{"球種": n_name, "單筒價格": n_price, "單價": u_p}])
                s_df_clean = settings_df[settings_df["球種"] != n_name] if not settings_df.empty else settings_df
                conn.update(worksheet="Settings", data=pd.concat([s_df_clean, new_entry], ignore_index=True))
                st.rerun()

# --- TAB 3: 歷史紀錄與編輯 ---
with tab3:
    if not records_df.empty:
        st.subheader("📜 歷史清單 (由新到舊)")
        df_display = records_df.copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display.sort_index(ascending=False), use_container_width=True)

        st.divider()
        
        # --- 編輯與刪除區塊 ---
        st.subheader("✏️ 編輯 / 🗑️ 刪除 紀錄")
        edit_idx = st.number_input("請輸入要操作的『編號』(Index)", min_value=1, max_value=len(records_df), step=1)
        
        # 抓取該列原始資料
        old_data = records_df.iloc[edit_idx - 1]
        
        with st.expander(f"點擊展開：修改第 {edit_idx} 筆紀錄"):
            with st.form("edit_form"):
                e_date = st.date_input("修改日期", datetime.strptime(str(old_data["日期"]), '%Y-%m-%d'))
                e_court = st.number_input("修改場地費", value=int(old_data["場地費"]))
                e_detail = st.text_input("修改球種明細 (手動修正文字)", value=old_data["球種明細"])
                e_ball_cost = st.number_input("修改用球成本", value=float(old_data["用球總成本"]))
                e_income = st.number_input("修改總收入", value=int(old_data["總收入"]))
                
                # 自動重新計算淨利
                e_profit = e_income - (e_court + e_ball_cost)
                st.write(f"💡 修正後淨利將為: ${e_profit}")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    save_edit = st.form_submit_button("💾 儲存修改")
                with col_btn2:
                    delete_rec = st.form_submit_button("🗑️ 刪除此筆 (不可復原)")

            if save_edit:
                records_df.iloc[edit_idx - 1] = [str(e_date), e_court, e_detail, e_ball_cost, e_income, e_profit]
                conn.update(worksheet="Records", data=records_df)
                st.success("✅ 資料已成功更新！")
                st.rerun()
                
            if delete_rec:
                new_df = records_df.drop(records_df.index[edit_idx - 1])
                conn.update(worksheet="Records", data=new_df)
                st.warning("⚠️ 紀錄已刪除")
                st.rerun()
    else:
        st.write("目前尚無歷史資料。")
