import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Gọi trực tiếp thư viện vnstock3 (Máy chủ Cloud sẽ tự nạp thư viện này)
try:
    from vnstock3 import Vnstock
except Exception as e:
    st.error("Đang khởi tạo môi trường Cloud, vui lòng làm mới trang sau vài giây...")

st.set_page_config(page_title="Bộ Lọc Cổ Phiếu CANSLIM - Cloud", layout="wide")

# --- CSS TỐI ƯU GIAO DIỆN PHONG CÁCH CHECKLIST ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden !important;}
    div[data-testid="stToolbar"] {visibility: hidden !important;}

    .main {background-color: #0e1117; color: #ffffff;}
    h1 {color: #10b981; text-align: center; font-size: 24px; font-weight: bold;}
    
    .stButton>button {width: 100%; background-color: #059669; color: white; border-radius: 10px; height: 3.2em; font-weight: bold; font-size: 16px; border: none;}
    .stButton>button:hover {background-color: #10b981; color: white;}

    .card-pass {
        background-color: #064e3b; 
        padding: 18px; 
        border-radius: 12px; 
        border: 2px solid #10b981; 
        margin-bottom: 15px;
        color: #e0e0e0;
    }
    .card-watch {
        background-color: #1e222d; 
        padding: 18px; 
        border-radius: 12px; 
        border: 1px solid #d97706; 
        margin-bottom: 15px;
        color: #e0e0e0;
    }
    .stock-header { 
        font-size: 22px; 
        margin-top: 0; 
        font-weight: bold;
    }
    .badge-pass {
        background-color: #10b981;
        color: white;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
    }
    .badge-fail {
        background-color: #ef4444;
        color: white;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
    }
    .check-item {
        font-size: 14px;
        margin: 6px 0;
    }
    .price-tag { color: #f59e0b; font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ BỘ LỌC CỔ PHIẾU CANSLIM CHÍNH THỐNG")
st.caption("Chạy 100% trên Đám mây - Không cần cài đặt trên thiết bị người dùng")

# --- KHU VỰC ĐIỀU CHỈNH TIÊU CHÍ ĐỊNH LƯỢNG CANSLIM ---
with st.expander("⚙️ **CẤU HÌNH TIÊU CHÍ BỘ LỌC CANSLIM**", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        min_c_eps = st.number_input("C - Tăng trưởng EPS/LNST Quý tối thiểu (%):", value=25.0, step=5.0)
        min_c_rev = st.number_input("C - Tăng trưởng Doanh thu Quý tối thiểu (%):", value=20.0, step=5.0)
        min_a_eps = st.number_input("A - Tăng trưởng LNST Năm gần nhất tối thiểu (%):", value=20.0, step=5.0)
    
    with col2:
        min_s_vol = st.number_input("S - Khối lượng bứt phá (x lần TB 20 phiên):", value=1.40, step=0.1)
        min_l_rs = st.number_input("L - Xếp hạng Sức mạnh giá RS Percentile (Top %):", value=80, max_value=99, min_value=50)
        filter_type = st.radio("Chế độ hiển thị:", ("Chỉ hiển thị cổ phiếu ĐẠT TẤT CẢ tiêu chí (Chuẩn O'Neil)", "Hiển thị cả Cổ phiếu Tiềm năng (Chỉ vi phạm 1 tiêu chí)"))

HOSE_ALL_398 = sorted(list(set([
    'AAA', 'AAM', 'ABR', 'ABS', 'ABT', 'ACB', 'ACC', 'ACG', 'ACI', 'ACL', 'ADG', 'ADP', 'ADS', 'AGG', 'AGM', 'AGR', 
    'ANV', 'APC', 'APG', 'APH', 'ASG', 'ASM', 'ASP', 'AST', 'BAF', 'BC2', 'BCE', 'BCG', 'BCM', 'BFC', 'BHN', 'BIC', 
    'BID', 'BKG', 'BMC', 'BMI', 'BMP', 'BRC', 'BSI', 'BTP', 'BTT', 'BVH', 'BWE', 'C32', 'C47', 'CCL', 'CDC', 'CHP', 
    'CIG', 'CII', 'CKG', 'CLC', 'CLL', 'CLW', 'CMG', 'CMX', 'CNG', 'COM', 'CRC', 'CSV', 'CTD', 'CTF', 'CTG', 'CTI', 
    'CTR', 'CTS', 'CVT', 'D2D', 'DAG', 'DAH', 'DBC', 'DBD', 'DBT', 'DC4', 'DCL', 'DCM', 'DGC', 'DGW', 'DHA', 'DHC', 
    'DHG', 'DHM', 'DIG', 'DLG', 'DMC', 'DPG', 'DPR', 'DQC', 'DRH', 'DRC', 'DPM', 'DSC', 'DTA', 'DTL', 'DVP', 'DXG', 
    'DXS', 'EIB', 'ELC', 'EVE', 'EVG', 'FCM', 'FCN', 'FIR', 'FIT', 'FMC', 'FPT', 'FRT', 'FTS', 'GAS', 'GEE', 'GEX', 
    'GIL', 'GMD', 'GSP', 'GTA', 'GVR', 'HAH', 'HAP', 'HAR', 'HAS', 'HAX', 'HBC', 'HCD', 'HCM', 'HDB', 'HDC', 'HDG', 
    'HHV', 'HIP', 'HIS', 'HMC', 'HNG', 'HPG', 'HPX', 'HQC', 'HRC', 'HSG', 'HT1', 'HTI', 'HTN', 'HTV', 'HU1', 'HUB', 
    'HVN', 'HVX', 'ICT', 'IDI', 'IJC', 'IMP', 'ITA', 'ITC', 'ITD', 'JVC', 'KBC', 'KDC', 'KDH', 'KHG', 'KHP', 'KMR', 
    'KOS', 'KSB', 'L10', 'LAF', 'LBM', 'LCG', 'LDG', 'LEC', 'LGL', 'LHG', 'LIX', 'LPB', 'LSS', 'MBB', 'MCP', 'MDG', 
    'MHG', 'MIG', 'MSH', 'MSN', 'MWG', 'NAF', 'NBB', 'NCT', 'NHA', 'NHH', 'NKG', 'NLG', 'NLT', 'NT2', 'NTL', 'NVL', 
    'OCB', 'OGC', 'OPC', 'PAN', 'PC1', 'PDN', 'PDR', 'PET', 'PGC', 'PGD', 'PGI', 'PLX', 'PNG', 'PNJ', 'POM', 
    'POW', 'PTB', 'PTC', 'PTL', 'PVD', 'PVT', 'QCG', 'RAL', 'REE', 'RDP', 'SAB', 'SB1', 'SBT', 'SBV', 'SC5', 'SCS', 
    'SFC', 'SFG', 'SGN', 'SHA', 'SHB', 'SHP', 'SIP', 'SJD', 'SJF', 'SKG', 'SMA', 'SMC', 'SPM', 'SRC', 'SRF', 'SSB', 
    'SSI', 'ST8', 'STB', 'STK', 'SVC', 'SVD', 'SVT', 'SZC', 'SZL', 'TAC', 'TBC', 'TCB', 'TCH', 'TCL', 'TCM', 'TCO', 
    'TCR', 'TDC', 'TDH', 'TDG', 'TDM', 'TDR', 'TEG', 'THG', 'THI', 'TIP', 'TI3', 'TIX', 'TLD', 'TLG', 'TLH', 'TMP', 
    'TMS', 'TNC', 'TNH', 'TNI', 'TNT', 'TPB', 'TPC', 'TRA', 'TRC', 'TS4', 'TSC', 'TTA', 'TTE', 'TTF', 'TVB', 'TVD', 
    'TYN', 'UIC', 'VAF', 'VCA', 'VCB', 'VCG', 'VCI', 'VGC', 'VMD', 'VND', 'VNE', 'VNG', 'VNL', 'VNM', 'VPB', 'VPD', 
    'VPG', 'VPH', 'VPI', 'VPS', 'VRC', 'VRE', 'VSC', 'VSH', 'VSI', 'VTB', 'VTO', 'YBM', 'YEG'
])))

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# LẤY BCTC TRÊN MÁY CHỦ CLOUD BẰNG VNSTOCK3
def fetch_fundamental_vnstock(symbol):
    try:
        stock = Vnstock().stock(symbol=symbol, source='VND')
        df_q = stock.finance.income_statement(period='quarter', lang='vi')
        c_eps_g, c_rev_g = None, None
        
        if not df_q.empty and len(df_q) >= 2:
            col_lnst = [c for c in df_q.columns if 'Lợi nhuận sau thuế' in c or 'cổ đông công ty mẹ' in c]
            lnst_col = col_lnst[0] if col_lnst else df_q.columns[1]
            
            col_rev = [c for c in df_q.columns if 'Thu nhập lãi thuần' in c or 'Doanh thu thuần' in c]
            rev_col = col_rev[0] if col_rev else df_q.columns[2]
            
            lnst_curr = float(df_q.iloc[0][lnst_col])
            lnst_prev = float(df_q.iloc[1][lnst_col])
            rev_curr = float(df_q.iloc[0][rev_col])
            rev_prev = float(df_q.iloc[1][rev_col])
            
            c_eps_g = ((lnst_curr - lnst_prev) / abs(lnst_prev)) * 100 if lnst_prev != 0 else (100.0 if lnst_curr > 0 else 0.0)
            c_rev_g = ((rev_curr - rev_prev) / abs(rev_prev)) * 100 if rev_prev != 0 else (100.0 if rev_curr > 0 else 0.0)

        df_y = stock.finance.income_statement(period='year', lang='vi')
        a_eps_g = None
        if not df_y.empty and len(df_y) >= 2:
            col_lnst_y = [c for c in df_y.columns if 'Lợi nhuận sau thuế' in c or 'cổ đông công ty mẹ' in c]
            lnst_y_col = col_lnst_y[0] if col_lnst_y else df_y.columns[1]
            
            lnst_y_curr = float(df_y.iloc[0][lnst_y_col])
            lnst_y_prev = float(df_y.iloc[1][lnst_y_col])
            
            a_eps_g = ((lnst_y_curr - lnst_y_prev) / abs(lnst_y_prev)) * 100 if lnst_y_prev != 0 else (100.0 if lnst_y_curr > 0 else 0.0)

        return round(c_eps_g, 1) if c_eps_g is not None else None, \
               round(c_rev_g, 1) if c_rev_g is not None else None, \
               round(a_eps_g, 1) if a_eps_g is not None else None
    except Exception:
        pass
    return None, None, None

@st.cache_data(ttl=43200)
def get_all_fundamentals_cached(symbols_tuple):
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_fundamental_vnstock, sym): sym for sym in symbols_tuple}
        for future in as_completed(future_to_symbol):
            sym = future_to_symbol[future]
            try:
                results[sym] = future.result(timeout=4.0)
            except Exception:
                results[sym] = (None, None, None)
    return results

def process_technical_data(symbol, fundamental_dict):
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    end_time = int(time.time())
    start_time = int((datetime.now() - timedelta(days=120)).timestamp())
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://dchart.vndirect.com.vn/'}
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol}&from={start_time}&to={end_time}"
    
    try:
        res = requests.get(url, headers=headers, timeout=2.5)
        if res.status_code == 200:
            js = res.json()
            if js.get('s') == 'ok' and len(js.get('c', [])) >= 22:
                closes = pd.Series(js['c'], dtype=float).apply(lambda x: x * 1000 if x < 1000 else x)
                vols = pd.Series(js['v'], dtype=float)
                
                price_now = closes.iloc[-1]
                vol_now = vols.iloc[-1]
                
                vol_avg20 = vols.iloc[-21:-1].mean()
                vol_spike = round(vol_now / vol_avg20, 2) if vol_avg20 > 0 else 1.0
                
                ma50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean()
                rsi_val = round(float(calculate_rsi(closes, 14).iloc[-1]), 1)
                
                c_eps, c_rev, a_eps = fundamental_dict.get(symbol, (None, None, None))
                
                return {
                    'Mã': symbol,
                    'Giá': float(price_now),
                    'Khối lượng': float(vol_now),
                    'Thời gian': now_str,
                    'MA50': float(ma50),
                    'Vol Spike': vol_spike,
                    'RSI': rsi_val if not pd.isna(rsi_val) else 50.0,
                    'C_EPS': c_eps,
                    'C_REV': c_rev,
                    'A_EPS': a_eps
                }
    except Exception:
        pass
    return None

def run_canslim_official_filter():
    tasks = HOSE_ALL_398
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    status_text.markdown("⏳ **Máy chủ Cloud đang tải BCTC từ Vnstock...**")
    progress_bar.progress(0.20)
    
    fundamental_dict = get_all_fundamentals_cached(tuple(tasks))
    
    results = []
    x = 0
    status_text.markdown("⏳ **Máy chủ Cloud đang tính toán chỉ báo kỹ thuật & Checklist...**")
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_symbol = {executor.submit(process_technical_data, sym, fundamental_dict): sym for sym in tasks}
        for future in as_completed(future_to_symbol):
            x += 1
            progress_bar.progress(0.20 + 0.80 * (x / len(tasks)))
            res = future.result()
            if res is not None:
                results.append(res)
                
    status_text.empty()
    progress_bar.empty()
    
    df = pd.DataFrame(results)
    if not df.empty:
        df['RS_Percentile'] = (df['RSI'].rank(pct=True) * 100).astype(int)
    return df

btn = st.button("🚀 BẮT ĐẦU QUÉT BỘ LỌC CANSLIM CHÍNH THỐNG")

if btn or "df_official" in st.session_state:
    if btn or "df_official" not in st.session_state:
        st.session_state["df_official"] = run_canslim_official_filter()
        
    df_all = st.session_state["df_official"]
    
    if not df_all.empty:
        processed_list = []
        for _, row in df_all.iterrows():
            pass_c = (row['C_EPS'] is not None and row['C_EPS'] >= min_c_eps) and \
                     (row['C_REV'] is not None and row['C_REV'] >= min_c_rev)
            pass_a = (row['A_EPS'] is not None and row['A_EPS'] >= min_a_eps)
            pass_s = (row['Vol Spike'] >= min_s_vol)
            pass_l = (row['RS_Percentile'] >= min_l_rs)
            pass_m = (row['Giá'] >= row['MA50'])
            
            checks = [pass_c, pass_a, pass_s, pass_l, pass_m]
            pass_count = sum(checks)
            
            if pass_count == 5:
                status = "CHUẨN CANSLIM"
            elif pass_count == 4:
                status = "TIỀM NĂNG (THEO DÕI)"
            else:
                status = "KHÔNG ĐẠT"
                
            processed_list.append({
                **row.to_dict(),
                'Pass_C': pass_c, 'Pass_A': pass_a, 'Pass_S': pass_s, 
                'Pass_L': pass_l, 'Pass_M': pass_m,
                'Pass_Count': pass_count,
                'Status': status
            })
            
        res_df = pd.DataFrame(processed_list)
        
        if "Chỉ hiển thị cổ phiếu ĐẠT TẤT CẢ" in filter_type:
            final_df = res_df[res_df['Status'] == "CHUẨN CANSLIM"]
        else:
            final_df = res_df[res_df['Status'].isin(["CHUẨN CANSLIM", "TIỀM NĂNG (THEO DÕI)"])]
            
        final_df = final_df.sort_values(by=['Pass_Count', 'RS_Percentile'], ascending=[False, False])
        
        st.markdown(f"### 📋 Kết quả: Tìm thấy **{len(final_df)}** cổ phiếu (Đã quét **{len(df_all)}** mã)")
        
        if final_df.empty:
            st.warning("Không có cổ phiếu nào đáp ứng đủ bộ tiêu chí. Bạn có thể hạ nhẹ tiêu chí ở mục Cấu hình!")
        
        for _, row in final_df.iterrows():
            card_class = "card-pass" if row['Status'] == "CHUẨN CANSLIM" else "card-watch"
            title_color = "#10b981" if row['Status'] == "CHUẨN CANSLIM" else "#f59e0b"
            
            def render_check(label, is_pass, detail_str):
                icon = "🟢 **ĐẠT**" if is_pass else "🔴 **KHÔNG ĐẠT**"
                return f"<div class='check-item'>• <b>{label}:</b> {icon} ({detail_str})</div>"
            
            c_str = f"LNST Quý: {f'+{row['C_EPS']}%' if row['C_EPS'] and row['C_EPS']>=0 else str(row['C_EPS'])+'%'} | Doanh thu: {f'+{row['C_REV']}%' if row['C_REV'] and row['C_REV']>=0 else str(row['C_REV'])+'%'}"
            a_str = f"LNST Năm: {f'+{row['A_EPS']}%' if row['A_EPS'] and row['A_EPS']>=0 else str(row['A_EPS'])+'%'}"
            s_str = f"Vol gấp {row['Vol Spike']} lần TB 20 phiên"
            l_str = f"Xếp hạng RS: Top {100 - row['RS_Percentile']}% toàn sàn"
            m_str = f"Giá ({int(round(row['Giá'])):,} VNĐ) {'nằm TRÊN' if row['Pass_M'] else 'nằm DƯỚI'} MA50 ({int(round(row['MA50'])):,} VNĐ)"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 class="stock-header" style="color: {title_color}; margin:0;">📌 Mã Cổ Phiếu: {row['Mã']}</h2>
                    <span class="{ 'badge-pass' if row['Status']=='CHUẨN CANSLIM' else 'badge-fail' }">{row['Status']} ({row['Pass_Count']}/5 Tiêu chí)</span>
                </div>
                <p style="margin-top: 8px;"><b>Giá khớp lệnh:</b> <span class="price-tag">{int(round(row['Giá'])):,} VNĐ</span> | <b>Khối lượng:</b> {int(row['Khối lượng']):,} CP</p>
                <hr style="border-color: #374151; margin: 10px 0;">
                <b>CHI TIẾT CHECKLIST CANSLIM CHÍNH THỐNG:</b>
                {render_check("C - Tăng trưởng Quý", row['Pass_C'], c_str)}
                {render_check("A - Tăng trưởng Năm", row['Pass_A'], a_str)}
                {render_check("S - Dòng tiền Bứt phá", row['Pass_S'], s_str)}
                {render_check("L - Cổ phiếu Leader", row['Pass_L'], l_str)}
                {render_check("M - Xu hướng Thị trường/Giá", row['Pass_M'], m_str)}
            </div>
            """, unsafe_allow_html=True)
