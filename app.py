import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Bộ Lọc Cổ Phiếu HOSE Realtime - CANSLIM & RS Leader", layout="wide")

# CSS Giao diện màu TÍM TRẦN (#ff00ff / #c026d3) & Ẩn Header cho Mobile
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden !important;}
    div[data-testid="stToolbar"] {visibility: hidden !important;}

    .main {background-color: #0e1117; color: #ffffff;}
    h1 {color: #c026d3; text-align: center; font-size: 24px; font-weight: bold;}
    
    .stButton>button {width: 100%; background-color: #9333ea; color: white; border-radius: 10px; height: 3.2em; font-weight: bold; font-size: 16px; border: none;}
    .stButton>button:hover {background-color: #c026d3; color: white;}
    
    div[data-baseweb="radio"] label div[aria-checked="true"] {
        background-color: #c026d3 !important;
        border-color: #ff00ff !important;
    }
    div[data-baseweb="radio"] label div[aria-checked="true"] > div {
        background-color: #ff00ff !important;
    }

    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #ff00ff !important;
        border-color: #ffffff !important;
        box-shadow: 0 0 10px #ff00ff !important;
    }
    div[data-baseweb="slider"] div {
        background-color: #c026d3 !important;
    }
    
    .card {
        background-color: #1e222d; 
        padding: 16px; 
        border-radius: 12px; 
        border: 1px solid #2a2e39; 
        margin-bottom: 15px;
        color: #e0e0e0;
    }
    .card h2.stock-header { 
        color: #ff00ff !important; 
        font-size: 20px; 
        margin-top: 0; 
        font-weight: bold;
        text-shadow: 0 0 8px rgba(255, 0, 255, 0.4);
    }
    .card p { font-size: 14px; margin: 6px 0; color: #d1d5db; }
    .price-tag { color: #ffcc00; font-size: 17px; font-weight: bold; }
    .time-note { color: #9ca3af; font-size: 12px; font-style: italic; }
    .rs-tag { color: #51cf66; font-weight: bold; }
    .vol-tag { color: #ff922b; font-weight: bold; }
    .badge {
        background-color: #9333ea;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📱 BỘ LỌC CỔ PHIẾU HOSE - CANSLIM & DÒNG TIỀN DỘNG")
st.caption("Tự động phân tích Tăng trưởng BCTC (Cách A) & Xếp hạng Leader RS Top 20% (Cách B)")

# --- KHU VỰC TÙY CHỌN BỘ LỌC NGAY MÀN HÌNH CHÍNH ---
with st.expander("⚙️ **NHẤP VÀO ĐÂY ĐỂ ĐIỀU CHỈNH TÙY CHỌN BỘ LỌC**", expanded=True):
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        analysis_method = st.radio(
            "Phương pháp phân tích:",
            ("1. Cơ bản (CANSLIM Tăng trưởng Quý)", "2. Kỹ thuật (Leader RS Top 20% & Dòng tiền)", "3. Lọc Kết hợp (Cơ bản + Kỹ thuật Khuyên dùng)")
        )
        min_rs = st.slider("Điểm sức mạnh giá (RS/RSI) tối thiểu:", 0, 100, 50)
        vol_ratio = st.slider("Đột biến khối lượng (x lần TB 20 phiên trước):", 0.0, 3.0, 0.5, step=0.05)

    with col_filter2:
        mode = st.radio(
            "Phương pháp chọn lọc:",
            ("1. Xu hướng & Dòng tiền mạnh (Kỹ thuật)", "2. Cổ phiếu bứt phá nền giá (Breakout)")
        )
        always_include_leaders = st.checkbox("Ưu tiên giữ lại nhóm Cổ phiếu Leader Top 20% RS & Tăng trưởng BCTC", value=True)
        
        st.markdown("**Khối lượng giao dịch cổ phiếu gần nhất:**")
        vol_op_col, vol_val_col = st.columns([1, 2])
        with vol_op_col:
            vol_operator = st.selectbox("Phép so sánh", ("≥", ">", "=", "<", "≤"), label_visibility="collapsed")
        with vol_val_col:
            target_vol = st.number_input("Số lượng cổ phiếu", min_value=0, max_value=10000000000, value=0, step=100000, label_visibility="collapsed")

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

def get_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504, 429])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- CÁCH A: LẤY VÀ PHÂN TÍCH TĂNG TRƯỞNG BCTC QUÝ TỪ API TCBS ---
def check_canslim_fundamental(symbol, session):
    try:
        url = f"https://apipub.tcbs.com.vn/tca/v1/finance/income-statement/{symbol}?type=quarter"
        res = session.get(url, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) >= 2:
                q_latest = data[0]
                q_previous = data[1]
                
                rev_growth = 0.0
                eps_growth = 0.0
                
                # Tính tăng trưởng Lợi nhuận sau thuế (C)
                lnst_curr = q_latest.get('postTaxProfit', 0)
                lnst_prev = q_previous.get('postTaxProfit', 0)
                if lnst_prev and lnst_prev > 0:
                    eps_growth = ((lnst_curr - lnst_prev) / abs(lnst_prev)) * 100
                
                # Tính tăng trưởng Doanh thu
                rev_curr = q_latest.get('revenue', 0)
                rev_prev = q_previous.get('revenue', 0)
                if rev_prev and rev_prev > 0:
                    rev_growth = ((rev_curr - rev_prev) / abs(rev_prev)) * 100

                # Tiêu chuẩn CANSLIM: LNST tăng > 20% hoặc Doanh thu tăng > 15%
                is_canslim_fundamental = (eps_growth >= 20.0) or (rev_growth >= 15.0)
                return is_canslim_fundamental, round(eps_growth, 1), round(rev_growth, 1)
    except Exception:
        pass
    return False, 0.0, 0.0

def process_single(symbol):
    now_str = datetime.now().strftime('%d/%m/%Y lúc %H:%M:%S')
    session = get_session()
    
    end_time = int(time.time())
    start_time = int((datetime.now() - timedelta(days=120)).timestamp())
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://dchart.vndirect.com.vn/'
    }
    
    url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol}&from={start_time}&to={end_time}"
    
    try:
        res = session.get(url, headers=headers, timeout=3.5)
        if res.status_code == 200:
            js = res.json()
            if js.get('s') == 'ok' and len(js.get('c', [])) >= 22:
                raw_closes = pd.Series(js['c'], dtype=float)
                vols = pd.Series(js['v'], dtype=float)
                
                # Nhân 1,000 quy đổi giá chuẩn VNĐ
                closes = raw_closes.apply(lambda x: x * 1000 if x < 1000 else x)
                
                price_now = closes.iloc[-1]
                vol_now = vols.iloc[-1]
                
                vol_avg20 = vols.iloc[-21:-1].mean()
                vol_spike = round(vol_now / vol_avg20, 2) if vol_avg20 > 0 else 1.0
                
                ma50_calc = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean()
                
                rsi_series = calculate_rsi(closes, 14)
                rsi_raw = rsi_series.iloc[-1]
                rsi_val = round(float(rsi_raw), 1) if not pd.isna(rsi_raw) else 50.0
                
                # Gọi kiểm tra tiêu chuẩn Tài chính (Cách A)
                is_fundamental, eps_g, rev_g = check_canslim_fundamental(symbol, session)
                
                return {
                    'Mã': symbol,
                    'Giá': float(price_now),
                    'Khối lượng': float(vol_now),
                    'Thời gian': now_str,
                    'Đường MA50': float(ma50_calc),
                    'Biến động Vol': vol_spike,
                    'Điểm RS': rsi_val,
                    'Tăng trưởng LNST Quý (%)': eps_g,
                    'Tăng trưởng Doanh thu (%)': rev_g,
                    'CANSLIM Cơ bản': is_fundamental,
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
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_symbol = {executor.submit(process_single, symbol): symbol for symbol in tasks}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            x += 1
            l_percent = round((x / y) * 100, 2)
            
            status_text.markdown(f"⏳ **Đang tự động phân tích BCTC & Kỹ thuật mã {symbol} ({x}/{y} mã - {l_percent}%)**")
            progress_bar.progress(x / y)
            
            res = future.result()
            if res is not None:
                results.append(res)
                
    status_text.empty()
    progress_bar.empty()
    
    df = pd.DataFrame(results)
    
    # --- CÁCH B: TỰ ĐỘNG LỌC LEADER THEO RS TOP 20% THỊ TRƯỜNG ---
    if not df.empty:
        # Xếp hạng RS trên toàn bộ cổ phiếu vừa cào được
        df['Xếp hạng RS Percentile'] = df['Điểm RS'].rank(pct=True) * 100
        # Cổ phiếu nằm trong Top 20% RS cao nhất thị trường và nằm trên MA50
        df['Leader RS Top 20%'] = (df['Xếp hạng RS Percentile'] >= 80.0) & (df['Giá'] >= df['Đường MA50'])
        
        # Đánh giá điểm tổng hợp CANSLIM (kết hợp cả A và B)
        def calc_score(row):
            score = row['Điểm RS'] * 0.5
            if row['CANSLIM Cơ bản']:
                score += 25
            if row['Leader RS Top 20%']:
                score += 25
            return int(min(max(score, 10), 99))
            
        df['Điểm CANSLIM Động'] = df.apply(calc_score, axis=1)

    return df

btn = st.button("🚀 BẮT ĐẦU RÀ SOÁT TOÀN BỘ SÀN HOSE (ĐỘNG)")

if btn or "df_cached" in st.session_state:
    if btn or "df_cached" not in st.session_state:
        st.session_state["df_cached"] = scan_all_data_with_progress()
            
    df_all = st.session_state["df_cached"]
    
    if not df_all.empty:
        if "1. Cơ bản" in analysis_method:
            cond = (
                (df_all['Điểm RS'] >= min_rs) & 
                (df_all['CANSLIM Cơ bản'] == True) &
                (df_all['Biến động Vol'] >= vol_ratio)
            )
        elif "2. Kỹ thuật" in analysis_method:
            if "1. Xu hướng" in mode:
                cond = (
                    (df_all['Điểm RS'] >= min_rs) & 
                    (df_all['Leader RS Top 20%'] == True) & 
                    (df_all['Biến động Vol'] >= vol_ratio)
                )
            else:
                cond = (
                    (df_all['Điểm RS'] >= min_rs) & 
                    (df_all['Biến động Vol'] >= max(vol_ratio, 0.8))
                )
        else: # Lọc Kết hợp
            cond = (
                (df_all['Điểm RS'] >= min_rs) & 
                ((df_all['CANSLIM Cơ bản'] == True) | (df_all['Leader RS Top 20%'] == True)) &
                (df_all['Biến động Vol'] >= vol_ratio)
            )
        
        res = df_all[cond]
        
        if always_include_leaders:
            leaders_df = df_all[(df_all['Leader RS Top 20%'] == True) | (df_all['CANSLIM Cơ bản'] == True)]
            res = pd.concat([res, leaders_df]).drop_duplicates(subset=['Mã'])
            
        if vol_operator == "≥":
            res = res[res['Khối lượng'] >= target_vol]
        elif vol_operator == ">":
            res = res[res['Khối lượng'] > target_vol]
        elif vol_operator == "=":
            res = res[res['Khối lượng'] == target_vol]
        elif vol_operator == "<":
            res = res[res['Khối lượng'] < target_vol]
        elif vol_operator == "≤":
            res = res[res['Khối lượng'] <= target_vol]

        st.markdown(f"### 🎉 Kết quả: Tìm thấy **{len(res)}** cổ phiếu đạt tiêu chí (Đã rà soát **{len(df_all)}** mã)")
        
        if len(res) == 0:
            st.warning("Không tìm thấy cổ phiếu nào thỏa mãn tiêu chí hiện tại. Hãy thử hạ bớt điểm RS hoặc biến động Vol ở góc trên!")
        else:
            for _, row in res.iterrows():
                # Tạo nhãn hiển thị trạng thái
                badges_html = ""
                if row['CANSLIM Cơ bản']:
                    badges_html += '<span class="badge" style="background-color:#059669;">BCTC Tăng trưởng tốt</span>'
                if row['Leader RS Top 20%']:
                    badges_html += '<span class="badge" style="background-color:#d97706;">Leader Top 20% RS</span>'

                st.markdown(f"""
                <div class="card">
                    <h2 class="stock-header">📌 Mã Cổ Phiếu: {row['Mã']} {badges_html}</h2>
                    <p><b>Giá thực tế khớp lệnh:</b> <span class="price-tag">{int(round(row['Giá'])):,} VNĐ</span> <span class="time-note">(Cập nhật: {row['Thời gian']})</span></p>
                    <p><b>Khối lượng giao dịch gần nhất:</b> <span class="vol-tag">{int(row['Khối lượng']):,} cổ phiếu</span></p>
                    <p><b>Sức mạnh giá (RSI 14):</b> <span class="rs-tag">{row['Điểm RS']}/100</span> (Xếp hạng RS: Top {100 - int(row['Xếp hạng RS Percentile'])}% thị trường)</p>
                    <p><b>Tăng trưởng LNST Quý gần nhất:</b> <span style="color:#00ff99; font-weight:bold;">+{row['Tăng trưởng LNST Quý (%)']}%</span> | <b>Doanh thu:</b> <span style="color:#00ff99; font-weight:bold;">+{row['Tăng trưởng Doanh thu (%)']}%</span></p>
                    <p><b>Dòng tiền thời gian thực:</b> Khối lượng gấp <span class="vol-tag">{row['Biến động Vol']} lần</span> TB 20 phiên trước</p>
                    <p><b>Xu hướng kỹ thuật:</b> <span style="color:#00ff99;">{row['Xu hướng']}</span> (Đường MA50: {int(round(row['Đường MA50'])):,} VNĐ)</p>
                    <p style="color:#ff00ff; font-size:14px; margin-top:8px;">💡 <b>Điểm đánh giá CANSLIM Động:</b> {row['Điểm CANSLIM Động']}/100</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Không thể lấy dữ liệu. Bạn hãy bấm lại nút Rà soát để thử lại!")
