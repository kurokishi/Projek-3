import streamlit as st
import sys
import os
import json
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests
from datetime import datetime, timedelta

# ======== Konfigurasi Awal ========
st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# ======== System Check ========
python_version = sys.version.split()[0]
st.sidebar.write(f"Python version: {python_version}")

# ======== Setup Session dengan Timeout ========
session = requests.Session()
session.timeout = 10  # 10 detik timeout

# ======== Dependency Fallbacks ========
class DummyModule:
    def __call__(self, *args, **kwargs):
        st.error("Fitur dinonaktifkan: Dependency tidak tersedia")
        return None
    def __getattr__(self, name):
        return self

# Setup fallbacks dengan error handling lebih baik
try:
    import yfinance as yf
    YFINANCE_ENABLED = True
except ImportError:
    yf = DummyModule()
    YFINANCE_ENABLED = False
    st.sidebar.error("⚠️ yfinance tidak terinstall (pip install yfinance)")

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
    TA_ENABLED = True
except ImportError:
    RSIIndicator = MACD = SMAIndicator = DummyModule()
    TA_ENABLED = False
    st.sidebar.error("⚠️ Library TA tidak terinstall (pip install ta)")

# ======== Fungsi Ambil Data Saham dengan Cache ========
def ambil_data_saham(ticker, cache_dir="cache", ttl_jam=1):
    if not YFINANCE_ENABLED:
        return pd.DataFrame(), {}

    os.makedirs(cache_dir, exist_ok=True)
    path_hist = os.path.join(cache_dir, f"{ticker}_hist.csv")
    path_info = os.path.join(cache_dir, f"{ticker}_info.json")

    now = datetime.now()

    def cache_valid(path):
        return os.path.exists(path) and (now - datetime.fromtimestamp(os.path.getmtime(path))) < timedelta(hours=ttl_jam)

    if cache_valid(path_hist):
        try:
            hist = pd.read_csv(path_hist, index_col=0, parse_dates=True)
            info = {}
            if os.path.exists(path_info):
                with open(path_info, "r") as f:
                    info = json.load(f)
            return hist, info
        except Exception as e:
            st.warning(f"⚠️ Gagal membaca cache untuk {ticker}, mengambil ulang...")

    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y", interval="1d")
        info = getattr(saham, "info", {})

        if not hist.empty:
            hist.to_csv(path_hist)
            with open(path_info, "w") as f:
                json.dump(info, f, indent=2)
            return hist, info
        else:
            st.warning(f"⚠️ Data historis {ticker} kosong")
            return pd.DataFrame(), info
    except Exception as e:
        st.error(f"❌ Gagal mengambil data {ticker}: {str(e)}")
        return pd.DataFrame(), {}

def format_rupiah(nilai):
    """Memformat angka menjadi format mata uang Rupiah"""
    try:
        return f"Rp{round(nilai):,}".replace(",", ".")
    except:
        return "Rp0"

def hitung_bunga_majemuk(modal_awal, tingkat_bunga, tahun):
    """Menghitung bunga majemuk untuk proyeksi investasi"""
    try:
        return modal_awal * (1 + tingkat_bunga/100) ** tahun
    except:
        return 0

def proyeksi_investasi(modal_awal, tambahan_bulanan, tingkat_bunga, tahun):
    """Menghitung proyeksi investasi dengan kontribusi bulanan"""
    hasil = []
    try:
        saldo = modal_awal
        for bulan in range(1, tahun * 12 + 1):
            saldo = saldo * (1 + tingkat_bunga/100/12) + tambahan_bulanan
            if bulan % 12 == 0:
                hasil.append((bulan//12, saldo))
    except:
        pass
    return hasil

def hitung_alokasi_dana(modal, portofolio, harga_saham_terkini):
    """Menghitung alokasi dana ke masing-masing saham dengan error handling"""
    try:
        total_nilai_portofolio = sum(data.get('total_investasi', 0) for data in portofolio.values())
        
        if total_nilai_portofolio == 0:
            return []
        
        alokasi = []
        for ticker, data in portofolio.items():
            try:
                proporsi = data.get('total_investasi', 0) / total_nilai_portofolio
                dana_dialokasikan = modal * proporsi
                
                harga_terkini = harga_saham_terkini.get(ticker, 0)
                if harga_terkini and harga_terkini > 0:
                    harga_per_lot = harga_terkini * 100  # 1 lot = 100 lembar
                    jumlah_lot = int(dana_dialokasikan // harga_per_lot)
                    nilai_pembelian = jumlah_lot * harga_per_lot
                else:
                    jumlah_lot = 0
                    nilai_pembelian = 0
                
                alokasi.append({
                    'Saham': ticker,
                    'Proporsi': proporsi,
                    'Dana Dialokasikan': dana_dialokasikan,
                    'Harga Terkini': harga_terkini,
                    'Jumlah Lot': jumlah_lot,
                    'Nilai Pembelian': nilai_pembelian
                })
            except Exception as e:
                st.error(f"Gagal menghitung alokasi untuk {ticker}: {str(e)}")
                continue
        
        return alokasi
    except Exception as e:
        st.error(f"Gagal menghitung alokasi dana: {str(e)}")
        return []

def tampilkan_status_sistem():
    """Menampilkan panel status dependency"""
    with st.expander("ℹ️ Status Sistem", expanded=True):
        st.write(f"**Python version:** {python_version}")
        st.write(f"**yfinance:** {'✅' if YFINANCE_ENABLED else '❌'}")
        st.write(f"**Technical Analysis:** {'✅' if TA_ENABLED else '❌'}")
        
        if not YFINANCE_ENABLED:
            st.warning("Fitur utama tidak tersedia tanpa yfinance")

# ======== Antarmuka Aplikasi yang Diperbaiki ========
def main():
    st.title("📊 Aplikasi Analisis Portofolio Saham")
    
    # Sidebar - Manajemen Portofolio dengan validasi lebih baik
    st.sidebar.header("Manajemen Portofolio")
    portofolio = muat_portofolio()
    
    with st.sidebar.form("tambah_saham"):
        st.write("**Tambahkan Saham Baru**")
        ticker = st.text_input("Kode Saham (contoh: AAPL, BBCA.JK)", key="input_ticker").upper().strip()
        lot = st.number_input("Jumlah Lot", min_value=1, step=1, key="input_lot", value=1)
        harga_per_lembar = st.number_input("Harga per Lembar (Rp)", min_value=1, step=100, key="input_harga", value=1000)
        
        if st.form_submit_button("💾 Simpan"):
            if ticker:
                try:
                    if ticker not in portofolio:
                        portofolio[ticker] = {
                            'lot': 0,
                            'harga_per_lembar': 0,
                            'total_investasi': 0,
                            'tgl_beli': datetime.now().strftime("%Y-%m-%d")
                        }
                    
                    portofolio[ticker]['lot'] += lot
                    portofolio[ticker]['harga_per_lembar'] = harga_per_lembar
                    portofolio[ticker]['total_investasi'] += lot * 100 * harga_per_lembar
                    
                    simpan_portofolio(portofolio)
                    st.success(f"Berhasil menambahkan {ticker}")
                    st.experimental_rerun()  # Refresh tampilan
                except Exception as e:
                    st.error(f"Gagal menambahkan saham: {str(e)}")
            else:
                st.error("Kode saham tidak boleh kosong")

    # Tombol Hapus Portofolio
    if st.sidebar.button("🗑️ Hapus Semua Portofolio", type="secondary"):
        portofolio = {}
        simpan_portofolio(portofolio)
        st.sidebar.success("Portofolio telah direset")
        st.experimental_rerun()

    # Status Sistem
    tampilkan_status_sistem()
    
    # Konten Utama dengan error handling lebih baik
    st.header("Portofolio Saat Ini")
    
    if not portofolio:
        st.info("Belum ada saham dalam portofolio. Silakan tambahkan saham dari sidebar.")
        return
    
    # Ambil harga terkini dengan progress bar
    harga_terkini = {}
    with st.spinner("Memperbarui data saham..."):
        for ticker in portofolio.keys():
            hist, _ = ambil_data_saham(ticker)
            if not hist.empty:
                harga_terkini[ticker] = hist['Close'].iloc[-1]
            else:
                harga_terkini[ticker] = portofolio[ticker].get('harga_per_lembar', 0)
    
    # Hitung total portofolio dengan nilai terkini
    try:
        total_portofolio = sum(
            data['lot'] * 100 * harga_terkini.get(ticker, data.get('harga_per_lembar', 0))
            for ticker, data in portofolio.items()
        )
        st.subheader(f"Total Nilai Portofolio: {format_rupiah(total_portofolio)}")
    except:
        st.warning("Gagal menghitung total portofolio")
    
    # Tab untuk portofolio dan analisis
    tab1, tab2 = st.tabs(["Detail Portofolio", "Analisis & Proyeksi"])
    
    with tab1:
        for ticker, data in portofolio.items():
            lot = data.get('lot', 0)
            harga_per_lembar = data.get('harga_per_lembar', 0)
            total_investasi = data.get('total_investasi', 0)
            tgl_beli = data.get('tgl_beli', '-')
            
            with st.expander(f"📈 {ticker} ({lot} lot)", expanded=True):
                # Tampilkan data dasar bahkan jika tidak bisa ambil data terbaru
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Harga Beli", format_rupiah(harga_per_lembar))
                col2.metric("Total Investasi", format_rupiah(total_investasi))
                col3.metric("Tanggal Beli", tgl_beli)
                
                # Coba tampilkan data terbaru jika ada
                if ticker in harga_terkini and harga_terkini[ticker] > 0:
                    harga_terkini_saham = harga_terkini[ticker]
                    col4.metric("Harga Terkini", format_rupiah(harga_terkini_saham))
                    
                    # Hitung keuntungan/kerugian
                    nilai_sekarang = lot * 100 * harga_terkini_saham
                    keuntungan = nilai_sekarang - total_investasi
                    persentase_keuntungan = (keuntungan / total_investasi) * 100 if total_investasi != 0 else 0
                    
                    st.metric("Nilai Saat Ini", 
                             format_rupiah(nilai_sekarang),
                             delta=f"{persentase_keuntungan:.2f}%")
                
                # Coba tampilkan grafik jika data tersedia
                hist, info = ambil_data_saham(ticker)
                if not hist.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        name="Harga Penutupan"
                    ))
                    fig.update_layout(
                        title=f"Performa {ticker}",
                        xaxis_title="Tanggal",
                        yaxis_title="Harga (Rp)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if TA_ENABLED:
                        st.subheader("Analisis Teknikal")
                        df_teknikal = hist.copy()
                        df_teknikal['RSI'] = RSIIndicator(df_teknikal['Close'], window=14).rsi()
                        
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(
                            x=df_teknikal.index,
                            y=df_teknikal['RSI'],
                            name="RSI 14"
                        ))
                        fig_rsi.update_layout(height=300)
                        st.plotly_chart(fig_rsi, use_container_width=True)
                else:
                    st.warning("Data historis tidak tersedia")
    
    with tab2:
        st.header("Analisis Bunga Majemuk & Proyeksi Investasi")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Kalkulator Bunga Majemuk")
            modal_awal = st.number_input("Modal Awal (Rp)", min_value=0, value=int(total_portofolio), step=100000)
            tingkat_bunga = st.number_input("Tingkat Bunga Tahunan (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
            tahun = st.slider("Jangka Waktu (tahun)", 1, 30, 10)
            
            hasil = hitung_bunga_majemuk(modal_awal, tingkat_bunga, tahun)
            st.metric(f"Nilai Investasi setelah {tahun} tahun", format_rupiah(hasil))
            
            # Grafik proyeksi
            tahun_list = list(range(tahun + 1))
            nilai_list = [hitung_bunga_majemuk(modal_awal, tingkat_bunga, t) for t in tahun_list]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=tahun_list,
                y=nilai_list,
                name="Proyeksi Nilai",
                mode='lines+markers'
            ))
            fig.update_layout(
                title=f"Proyeksi Bunga Majemuk {tahun} Tahun",
                xaxis_title="Tahun",
                yaxis_title="Nilai Investasi (Rp)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Proyeksi dengan Tambahan Investasi Bulanan")
            tambahan_bulanan = st.number_input("Tambahan Investasi Bulanan (Rp)", min_value=0, value=1000000, step=100000)
            
            hasil_proyeksi = proyeksi_investasi(modal_awal, tambahan_bulanan, tingkat_bunga, tahun)
            
            # Tabel hasil proyeksi
            df_proyeksi = pd.DataFrame(hasil_proyeksi, columns=['Tahun', 'Nilai'])
            df_proyeksi['Nilai'] = df_proyeksi['Nilai'].apply(lambda x: format_rupiah(x))
            st.table(df_proyeksi)
            
            # Grafik proyeksi dengan tambahan bulanan
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_proyeksi['Tahun'],
                y=[float(x.replace('Rp', '').replace('.', '')) for x in df_proyeksi['Nilai']],
                name="Proyeksi Nilai",
                mode='lines+markers'
            ))
            fig2.update_layout(
                title=f"Proyeksi dengan Tambahan Bulanan {tahun} Tahun",
                xaxis_title="Tahun",
                yaxis_title="Nilai Investasi (Rp)",
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Alokasi Dana dan Pembelian Saham
        st.subheader("Alokasi Dana dan Pembelian Saham")
        
        col3, col4 = st.columns(2)
        
        with col3:
            modal_tersedia = st.number_input("Modal yang Tersedia (Rp)", min_value=0, value=10000000, step=1000000)
            
            if st.button("Hitung Alokasi Dana"):
                if not portofolio:
                    st.warning("Portofolio masih kosong. Silakan tambahkan saham terlebih dahulu.")
                else:
                    alokasi_dana = hitung_alokasi_dana(modal_tersedia, portofolio, harga_terkini)
                    
                    if alokasi_dana:
                        df_alokasi = pd.DataFrame(alokasi_dana)
                        df_alokasi['Proporsi'] = df_alokasi['Proporsi'].apply(lambda x: f"{x*100:.1f}%")
                        df_alokasi['Dana Dialokasikan'] = df_alokasi['Dana Dialokasikan'].apply(format_rupiah)
                        df_alokasi['Harga Terkini'] = df_alokasi['Harga Terkini'].apply(format_rupiah)
                        df_alokasi['Nilai Pembelian'] = df_alokasi['Nilai Pembelian'].apply(format_rupiah)
                        
                        st.write("### Alokasi Dana ke Masing-masing Saham")
                        st.dataframe(df_alokasi[['Saham', 'Proporsi', 'Dana Dialokasikan', 
                                               'Harga Terkini', 'Jumlah Lot', 'Nilai Pembelian']])
                        
                        total_teralokasi = sum(item['Nilai Pembelian'] for item in alokasi_dana)
                        sisa_dana = modal_tersedia - total_teralokasi
                        
                        st.metric("Total Dana Teralokasi", format_rupiah(total_teralokasi))
                        st.metric("Sisa Dana", format_rupiah(sisa_dana))
        
        with col4:
            if 'alokasi_dana' in locals():
                st.write("### Visualisasi Alokasi Dana")
                fig_pie = go.Figure()
                fig_pie.add_trace(go.Pie(
                    labels=df_alokasi['Saham'],
                    values=[float(x.replace('Rp', '').replace('.', '')) for x in df_alokasi['Nilai Pembelian']],
                    textinfo='label+percent',
                    insidetextorientation='radial'
                ))
                fig_pie.update_layout(
                    title="Proporsi Alokasi Dana",
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)

if __name__ == "__main__":
    main()
