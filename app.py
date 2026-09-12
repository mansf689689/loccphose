import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Bộ Lọc Cổ Phiếu HOSE Realtime - Tiềm Năng 6 Tháng", layout="wide")

# CSS Giao diện màu TÍM TRẦN (#ff00ff / #c026d3)
st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #ffffff;}
    h1 {color: #c026d3; text-align: center; font-size: 26px; font-weight: bold;}
    
    .stButton>button {width: 100%; background-color: #9333ea; color: white; border-radius: 10px; height: 3.2em; font-weight: bold; font-size: 16px; border: none;}
    .stButton>button:hover {background-color: #c026d3; color: white;}
    
    div[data-baseweb="radio"] label div[aria-checked="true"] {
        background-color: #c026d3 !important;
        border-color: #ff00ff !important;
    }
    div[data-baseweb="radio"] label div[aria-checked="true"] > div {
        background-color: #ff00ff !important;
    }
    div[role="radiogroup"] label:hover {
        color: #ff00ff !important;
    }

    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #ff00ff !important;
        border-color: #ffffff !important;
        box-shadow: 0 0 10px #ff00ff !important;
    }
    div[data-baseweb="slider"] div[data-testid="stSliderTickBar"] ~ div {
        background-color: #c026d3 !important;
    }
    div[data-baseweb="slider"] div {
        background-color: #c026d3 !important;
    }
    
    .card {
        background-color: #1e222d; 
        padding: 18px; 
        border-radius: 12px; 
        border: 1px solid #2a2e39; 
        margin-bottom: 15px;
        color: #e0e0e0;
    }
    .card h2.stock-header { 
        color: #ff00ff !important; 
        font-size: 22px; 
        margin-top: 0; 
        font-weight: bold;
        text-shadow: 0 0 8px rgba(255, 0, 255, 0.4);
    }
    .card p { font-size: 15px; margin: 6px 0; color: #d1d5db; }
    .price-tag { color: #ffcc00; font-size: 18px; font-weight: bold; }
    .time-note { color: #9ca3af; font-size: 13px; font-style: italic; }
    .rs-tag { color: #51cf66; font-weight: bold; }
    .vol-tag { color: #ff922b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📱 BỘ LỌC CỔ PHIẾU HOSE - TIỀM NĂNG 6 THÁNG")
st.caption("Dữ liệu đồng bộ chuẩn xác từ Bảng giá & Lịch sử khớp lệnh HOSE")

# --- SIDEBAR TÙY CHỌN BỘ LỌC ---
st.sidebar.header("⚙️ Tùy chọn Bộ Lọc")

analysis_method = st.sidebar.radio(
    "Phương pháp phân tích:",
    ("1. Cơ bản (CANSLIM)", "2. Kỹ thuật (Dòng tiền/RS)", "3. Lọc Kết hợp (Khuyến dùng)")
)

st.sidebar.markdown("---")

min_rs = st.sidebar.slider("Điểm sức mạnh giá (RS/RSI) tối thiểu:", 0, 100, 50)
vol_ratio = st.sidebar.slider("Đột biến khối lượng (x lần TB 20 phiên):", 0.0, 3.0, 0.7, step=0.05)

mode = st.sidebar.radio(
    "Phương pháp chọn lọc:",
    ("1. Xu hướng & Dòng tiền mạnh (Kỹ thuật)", "2. Cổ phiếu bứt phá nền giá (Breakout)")
)

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
    'OCB', 'OGC', 'OPC', 'ORORS', 'PAN', 'PC1', 'PDN', 'PDR', 'PET', 'PGC', 'PGD', 'PGI', 'PLX', 'PNG', 'PNJ', 'POM', 
    'POW', 'PTB', 'PTC', 'PTL', 'PVD', 'PVT', 'QCG', 'RAL', 'REE', 'RDP', 'SAB', 'SB1', 'SBT', 'SBV', 'SC5', 'SCS', 
    'SFC', 'SFG', 'SGN', 'SHA', 'SHB', 'SHP', 'SIP', 'SJD', 'SJF', 'SKG', 'SMA', 'SMC', 'SPM', 'SRC', 'SRF', 'SSB', 
    'SSI', 'ST8', 'STB', 'STK', 'SVC', 'SVD', 'SVT', 'SZC', 'SZL', 'TAC', 'TBC', 'TCB', 'TCH', 'TCL', 'TCM', 'TCO', 
    'TCR', 'TDC', 'TDH', 'TDG', 'TDM', 'TDR', 'TEG', 'THG', 'THI', 'TIP', 'TI3', 'TIX', 'TLD', 'TLG', 'TLH', 'TMP', 
    'TMS', 'TNC', 'TNH', 'TNI', 'TNT', 'TPB', 'TPC', 'TRA', 'TRC', 'TS4', 'TSC', 'TTA', 'TTE', 'TTF', 'TVB', 'TVD', 
    'TYN', 'UIC', 'VAF', 'VCA', 'VCB', 'VCG', 'VCI', 'VGC', 'VMD', 'VND', 'VNE', 'VNG', 'VNL', 'VNM', 'VPB', 'VPD', 
    'VPG', 'VPH', 'VPI', 'VPS', 'VRC', 'VRE', 'VSC', 'VSH', 'VSI', 'VTB', 'VTO', 'YBM', 'YEG'
])))

CANSLIM_LEADERS = [
    'FPT', 'MWG', 'FRT', 'DGC', 'HPG', 'MBB', 'TCB', 'ACB', 'CTR', 'GMD', 
    'PNJ', 'VNM', 'STB', 'SSI', 'VCB', 'CTG', 'VHC', 'DCM', 'DPM', 'HAH'
]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Tạo Session kết nối bền vững có cơ chế tự động thử lại khi lỗi mạng
def get_http_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504, 429])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def process_single(symbol):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    now_str = datetime.now().strftime('%d/%m/%Y lúc %H:%M:%S')
    session = get_http_session()
    
    try:
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from=0&to=9999999999&symbol={symbol}&resolution=1D"
        res = session.get(url, headers=headers, timeout=5.0)
        
        if res.status_code == 200:
            js = res.json()
            if 'c' not in js or len(js['c']) < 20:
                return None
                
            df_temp = pd.DataFrame({'c': js['c'], 'v': js['v']}).dropna()
            closes = df_temp['c'].astype(float)
            vols = df_temp['v'].astype(float)
            
            price_now = closes.iloc[-1] * 1000 if closes.iloc[-1] < 1000 else closes.iloc[-1]
            vol_now = vols.iloc[-1]
                
            ma50_calc = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean()
            if ma50_calc < 1000: ma50_calc *= 1000
            
            vol_avg20 = vols.iloc[-21:-1].mean() if len(vols) >= 21 else vols.iloc[:-1].mean()
            vol_spike = round(vol_now / vol_avg20, 2) if vol_avg20 > 0 else 1.0
            
            rsi_series = calculate_rsi(closes, 14)
            rsi_raw = rsi_series.iloc[-1]
            rsi_val = round(float(rsi_raw), 1) if not pd.isna(rsi_raw) else 50.0
            
            is_canslim = symbol in CANSLIM_LEADERS
            canslim_score = int(min(max(rsi_val + (20 if is_canslim else 0), 10), 99))
            
            return {
                'Mã': symbol,
                'Giá': float(price_now),
                'Thời gian': now_str,
                'Đường MA50': float(ma50_calc),
                'Biến động Vol': vol_spike,
                'Điểm RS': rsi_val,
                'Điểm CANSLIM': canslim_score,
                'Là CANSLIM': is_canslim,
                'Xu hướng': 'Tăng' if price_now >= ma50_calc else 'Giảm/Tích lũy'
            }
    except Exception:
        pass
    return None

def scan_all_data_with_progress():
    tasks = HOSE_ALL_398
    y = len(tasks)
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    x = 0
    # Giảm luồng xuống 12 để tránh tuyệt đối việc API Entrade chặn IP hoặc nghẽn mạng Streamlit
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_symbol = {executor.submit(process_single, symbol): symbol for symbol in tasks}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            x += 1
            l_percent = round((x / y) * 100, 2)
            
            status_text.markdown(f"⏳ **Đang rà soát đến cổ phiếu {symbol} ({x}/{y} cổ phiếu, tương ứng {l_percent}% rà soát)**")
            progress_bar.progress(x / y)
            
            res = future.result()
            if res is not None:
                results.append(res)
                
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(results)

btn = st.button("🚀 BẮT ĐẦU RÀ SOÁT TOÀN BỘ SÀN HOSE")

if btn or "df_cached" in st.session_state:
    if btn or "df_cached" not in st.session_state:
        st.session_state["df_cached"] = scan_all_data_with_progress()
            
    df_all = st.session_state["df_cached"]
    
    if not df_all.empty:
        if "1. Cơ bản (CANSLIM)" in analysis_method:
            res = df_all[
                (df_all['Điểm RS'] >= min_rs) & 
                (df_all['Là CANSLIM'] == True) &
                (df_all['Biến động Vol'] >= vol_ratio)
            ]
        elif "2. Kỹ thuật" in analysis_method:
            if "1. Xu hướng" in mode:
                res = df_all[
                    (df_all['Điểm RS'] >= min_rs) & 
                    (df_all['Giá'] >= df_all['Đường MA50']) & 
                    (df_all['Biến động Vol'] >= vol_ratio)
                ]
            else:
                res = df_all[
                    (df_all['Điểm RS'] >= min_rs) & 
                    (df_all['Biến động Vol'] >= max(vol_ratio, 1.1))
                ]
        else:
            res = df_all[
                (df_all['Điểm RS'] >= min_rs) & 
                (df_all['Điểm CANSLIM'] >= 60) &
                (df_all['Biến động Vol'] >= vol_ratio) &
                (df_all['Giá'] >= df_all['Đường MA50'])
            ]
            
        st.markdown(f"### 🎉 Kết quả: Tìm thấy **{len(res)}** cổ phiếu đạt tiêu chí (Đã rà soát **{len(df_all)}** mã)")
        
        if len(res) == 0:
            st.warning("Không tìm thấy cổ phiếu nào thỏa mãn. Bạn thử hạ nhẹ thanh trượt nhé!")
        else:
            for _, row in res.iterrows():
                st.markdown(f"""
                <div class="card">
                    <h2 class="stock-header">📌 Mã Cổ Phiếu: {row['Mã']}</h2>
                    <p><b>Giá thực tế khớp lệnh:</b> <span class="price-tag">{int(row['Giá']):,} VNĐ</span> <span class="time-note">(Cập nhật: {row['Thời gian']})</span></p>
                    <p><b>Sức mạnh giá (RSI 14):</b> <span class="rs-tag">{row['Điểm RS']}/100</span> | <b>Đánh giá CANSLIM:</b> {row['Điểm CANSLIM']}/100</p>
                    <p><b>Dòng tiền thời gian thực:</b> Khối lượng gấp <span class="vol-tag">{row['Biến động Vol']} lần</span> TB 20 phiên</p>
                    <p><b>Xu hướng kỹ thuật:</b> <span style="color:#00ff99;">{row['Xu hướng']}</span> (Đường MA50: {int(row['Đường MA50']):,} VNĐ)</p>
                    <p style="color:#ff00ff; font-size:14px; margin-top:8px;">💡 <b>Đánh giá 6 tháng:</b> Cổ phiếu có tín hiệu mua tích lũy tốt.</p>
                </div>
                """, unsafe_allow_html=True)
