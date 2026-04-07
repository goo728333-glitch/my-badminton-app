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

# --- 2. 建立連線與強制重置功能 ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if st.sidebar.button("🚨 系統修復 (清除所有錯誤)"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

# --- 3. 終極穩定讀取函數 ---
def load_data_v6(worksheet_name, standard_cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
        if df is None or df.empty:
            return pd.DataFrame(columns=standard_cols)
        # 強制修正標題，確保程式內部邏輯一致
        df.columns = standard_cols[:len(df.columns)]
        return df
    except:
        return pd.DataFrame(columns=standard_cols)

COL_S = ["球種", "單筒價格", "單價"]
COL_R = ["日期", "場地費", "球種明細", "用球總成本", "總收入", "淨利"]

settings_df = load_data_v6("Settings", COL_S)
records_df = load_data_v6("Records", COL_R)

st.title("🏸 羽球管家 Pro")
tab1, tab2, tab3 = st.tabs(["📝 新增開團", "⚙️ 球種設定", "📜 歷史紀錄 / 編輯"])

# --- TAB 1: 新增開團 ---
with tab1:
    if 'ball_usage' not in st.session_state or not isinstance(st.session_state.ball_usage, list):
        st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": "", "count": 0}]
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1: date = st.date_input("日期", datetime.now())
        with c2:
            court_u = st.number_input("場地單位 ($250/位)", min_value=1, value=2, key="main_court")
            court_f = court_u * 250
            st.caption(f"🏟️ 場地費：${court_f}")

        st.write("#### 💰 收入人數")
        i1, i2, i3 = st.columns(3)
        with i1: p140 = st.number_input("$140", min_value=0, step=1, key="main_140")
        with i2: p180 = st.number_input("$180", min_value=0, step=1, key="main_180")
        with i3: p240 = st.number_input("$240", min_value=0, step=1, key="main_240")
        total_in = (p140 * 140) + (p180 * 180) + (p240 * 240)
        st.info(f"💵 總收入：**${total_in}**")

        st.write("#### 🎾 用球明細")
        b_opts = settings_df["球種"].unique().tolist() if not settings_df.empty else []
        
        if b_opts:
            total_b_cost = 0.0
            details = []
            for idx, row in enumerate(st.session_state.ball_usage):
                uid = row.get("id", str(time.time()))
                r1, r2, r3 = st.columns([5, 4, 1.5])
                with r1:
                    cur = row.get('ball_type', "")
                    b_idx = b_opts.index(cur) if cur in b_opts else 0
                    row['ball_type'] = st.selectbox(f"球種", b_opts, index=b_idx, key=f"sel_{uid}", label_visibility="collapsed")
                with r2:
                    row['count'] = st.number_input(f"顆數", min_value=0, value=row.get('count', 0), key=f"num_{uid}", label_visibility="collapsed")
                with r3:
                    if st.button("❌", key=f"del_{uid}"):
                        st.session_state.ball_usage.pop(idx)
                        st.rerun()
                
                up = float(settings_df.loc[settings_df["球種"] == row['ball_type'], "單價"].values[0])
                total_b_cost += up * row['count']
                if row['count'] > 0: details.append(f"{row['ball_type']}x{row['count']}")
            
            if st.button("➕ 新增球種項目"):
                st.session_state.ball_usage.append({"id": str(time.time()), "ball_type": b_opts[0], "count": 0})
                st.rerun()

            net = total_in - (court_f + total_b_cost)
            st.write("---")
            if st.button("🚀 儲存紀錄", use_container_width=True):
                new_data = pd.DataFrame([[str(date), int(court_f), ", ".join(details), round(total_b_cost, 1), int(total_in), round(net, 1)]], columns=COL_R)
                conn.update(worksheet="Records", data=pd.concat([records_df, new_data], ignore_index=True))
                st.session_state.ball_usage = [{"id": str(time.time()), "ball_type": b_opts[0], "count": 0}]
                st.success("儲存成功！")
                st.rerun()
        else:
            st.warning("請先設定球種資料")

# --- TAB 2: 球種設定 ---
with tab2:
    st.subheader("🛠 球種清單")
    st.dataframe(settings_df, use_container_width=True)
    with st.form("add_ball_form"):
        name = st.text_input("球種名稱")
        price = st.number_input("單筒價格", value=0.0)
        if st.form_submit_button("儲存"):
            if name and price > 0:
                new_b = pd.DataFrame([[name, price, round(price/12, 2)]], columns=COL_S)
                conn.update(worksheet="Settings", data=pd.concat([settings_df, new_b], ignore_index=True))
                st.rerun()

# --- TAB 3: 編輯與歷史紀錄 ---
with tab3:
    if not records_df.empty:
        st.subheader("📜 歷史紀錄 (編號由 1 開始)")
        df_view = records_df.copy()
        df_view.index = range(1, len(df_view) + 1)
        st.dataframe(df_view.sort_index(ascending=False), use_container_width=True)

        st.divider()
        st.subheader("✏️ 快速編輯區")
        edit_no = st.number_input("輸入欲操作的編號", min_value=1, max_value=len(records_df), step=1, key="edit_selector")
        
        # --- 鋼鐵級安全取值邏輯 ---
        # 將該列轉成純 List，完全放棄欄位名稱存取，避免 KeyError
        target_list = records_df.iloc[edit_no - 1].tolist()
        
        with st.expander(f"展開編輯第 {edit_no} 筆資料"):
            with st.form("edit_v6_form"):
                try: de = datetime.strptime(str(target_list[0]), '%Y-%m-%d')
                except: de = datetime.now()
                
                f_date = st.date_input("日期", de)
                f_court = st.number_input("場地費", value=int(target_list[1]))
                f_detail = st.text_input("球種明細", value=str(target_list[2]))
                f_bcost = st.number_input("用球總成本", value=float(target_list[3]))
                f_income = st.number_input("總收入", value=int(target_list[4]))
                f_net = f_income - (f_court + f_bcost)
                
                st.write(f"📊 修正後淨利將為：${f_net}")
                
                btn1, btn2 = st.columns(2)
                with btn1: 
                    if st.form_submit_button("💾 確認修改"):
                        records_df.iloc[edit_no - 1] = [str(f_date), int(f_court), f_detail, f_bcost, int(f_income), f_net]
                        conn.update(worksheet="Records", data=records_df)
                        st.success("更新成功")
                        st.rerun()
                with btn2:
                    if st.form_submit_button("🗑️ 刪除紀錄"):
                        new_records = records_df.drop(records_df.index[edit_no - 1])
                        conn.update(worksheet="Records", data=new_records)
                        st.rerun()
