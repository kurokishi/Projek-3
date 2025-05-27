# ... (Impor library tambahan di bagian atas)
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler

# ======= FUNGSI ANALISIS LANJUTAN =======

def analisis_valuasi_mendalam(info, harga_terakhir):
    """Analisis fundamental dengan lebih detail"""
    hasil = {
        'PER_vs_Industri': 'N/A',
        'Margin_Keamanan': 'N/A',
        'Nilai_Intrinsik': 'N/A'
    }
    
    try:
        # PER Comparasion
        avg_industry_pe = info.get('industryPe', None)
        current_pe = info.get('trailingPE', None)
        
        if current_pe and avg_industry_pe:
            selisih = ((current_pe - avg_industry_pe) / avg_industry_pe) * 100
            hasil['PER_vs_Industri'] = f"{'Di bawah' if selisih < 0 else 'Di atas'} rata-rata industri ({selisih:.1f}%)"
        
        # DCF Simplified
        growth = info.get('earningsGrowth', 0.05)
        div = info.get('dividendRate', 0)
        discount_rate = 0.1  # Asumsi 10%
        
        if growth and div:
            nilai_intrinsik = div / (discount_rate - growth)
            margin_keamanan = ((nilai_intrinsik - harga_terakhir) / harga_terakhir) * 100
            hasil['Nilai_Intrinsik'] = format_rupiah(nilai_intrinsik)
            hasil['Margin_Keamanan'] = f"{margin_keamanan:.1f}%"
            
    except Exception as e:
        st.error(f"Error valuasi: {str(e)}")
    
    return hasil

def prediksi_harga_lstm(df, periode=30):
    """Prediksi harga dengan model LSTM sederhana"""
    try:
        from keras.models import Sequential
        from keras.layers import LSTM, Dense
        
        # Normalisasi data
        scaler = MinMaxScaler()
        data = scaler.fit_transform(df['Close'].values.reshape(-1,1))
        
        # Siapkan dataset
        X, y = [], []
        for i in range(periode, len(data)):
            X.append(data[i-periode:i, 0])
            y.append(data[i, 0])
        
        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        # Bangun model
        model = Sequential()
        model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)))
        model.add(LSTM(50))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        
        # Training (sederhana)
        model.fit(X, y, epochs=10, batch_size=32, verbose=0)
        
        # Prediksi
        inputs = data[-periode:]
        inputs = scaler.transform(inputs)
        
        X_test = np.array([inputs])
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        
        pred = model.predict(X_test)
        pred = scaler.inverse_transform(pred)[0][0]
        
        return pred
    except Exception as e:
        st.warning(f"Prediksi LSTM gagal: {str(e)}")
        return None

def scrape_sentimen(ticker):
    """Scraping berita dan analisis sentimen sederhana"""
    try:
        # Contoh scraping (mockup)
        berita = {
            'judul': [],
            'sentimen': []
        }
        
        # Mock data - implementasi nyata bisa pakai BeautifulSoup/API
        sample_news = [
            ("Laba {ticker} tumbuh 20% di Q3 2023", "positif"),
            ("{ticker} hadapi risiko regulasi baru", "negatif")
        ]
        
        for judul, sentimen in sample_news:
            berita['judul'].append(judul.format(ticker=ticker))
            berita['sentimen'].append(sentimen)
        
        return berita
    except:
        return None

# ======= UI/UX IMPROVEMENTS =======

# Tab baru untuk analisis mendalam
tab1, tab2, tab3, tab4 = st.tabs(["Portofolio", "Analisis Mendalam", "Prediksi", "Berita"])

with tab2:
    st.header("🔍 Analisis Fundamental Mendalam")
    
    for ticker in portofolio.keys():
        with st.expander(f"Analisis Lanjutan {ticker}"):
            hist, info = ambil_data_saham(ticker)
            if hist.empty:
                continue
                
            harga_terakhir = hist['Close'][-1]
            valuasi = analisis_valuasi_mendalam(info, harga_terakhir)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("PER vs Industri", valuasi['PER_vs_Industri'])
                st.metric("Nilai Intrinsik (DCF)", valuasi['Nilai_Intrinsik'])
            
            with col2:
                st.metric("Margin Keamanan", valuasi['Margin_Keamanan'])
                
                # Analisis dividend safety
                payout = info.get('payoutRatio', None)
                if payout:
                    st.progress(payout)
                    st.caption(f"Payout Ratio: {payout*100:.1f}%")
                    st.write("🟢 Aman" if payout < 0.7 else "⚠️ Berisiko")

with tab3:
    st.header("🔮 Prediksi Harga & Rekomendasi")
    
    pilihan_ticker = st.selectbox("Pilih Saham untuk Prediksi", list(portofolio.keys()))
    
    if pilihan_ticker:
        hist, _ = ambil_data_saham(pilihan_ticker)
        if not hist.empty:
            # Prediksi dengan LSTM
            pred_harga = prediksi_harga_lstm(hist)
            
            # Prediksi dengan Random Forest
            df = hist.copy()
            df['MA_7'] = df['Close'].rolling(7).mean()
            df['Volatility'] = df['Close'].pct_change().rolling(14).std()
            df.dropna(inplace=True)
            
            X = df[['MA_7', 'Volatility']]
            y = df['Close']
            
            model = RandomForestRegressor(n_estimators=100)
            model.fit(X[:-30], y[:-30])  # Latih dengan data historis
            
            # Prediksi 30 hari ke depan
            pred_rf = model.predict(X[-30:])
            
            # Visualisasi
            fig, ax = plt.subplots(figsize=(10,5))
            ax.plot(df.index[-60:], df['Close'][-60:], label='Aktual')
            ax.plot(df.index[-30:], pred_rf, label='Prediksi RF', linestyle='--')
            
            if pred_harga:
                ax.axhline(y=pred_harga, color='r', linestyle=':', 
                          label=f'Prediksi LSTM: {format_rupiah(pred_harga)}')
            
            ax.legend()
            ax.set_title(f"Prediksi Harga {pilihan_ticker}")
            st.pyplot(fig)
            
            # Rekomendasi berbasis prediksi
            if pred_harga:
                perubahan = ((pred_harga - df['Close'][-1]) / df['Close'][-1]) * 100
                rekomendasi = "BELI" if perubahan > 5 else "Tahan" if perubahan > -5 else "JUAL"
                st.metric("Rekomendasi AI", rekomendasi, 
                         f"{perubahan:.1f}% dari harga sekarang")

with tab4:
    st.header("📰 Berita & Sentimen Saham")
    
    for ticker in portofolio.keys():
        with st.expander(f"Berita {ticker}"):
            berita = scrape_sentimen(ticker)
            
            if berita:
                for judul, sentimen in zip(berita['judul'], berita['sentimen']):
                    emoji = "👍" if sentimen == "positif" else "👎"
                    st.write(f"{emoji} {judul}")
            else:
                st.warning("Tidak dapat mengambil berita terkini")

# ======= FITUR RISK MANAGEMENT =======

st.sidebar.header("Manajemen Risiko")

# Hitung beta portofolio
if len(portofolio) > 0:
    try:
        returns = []
        for ticker in portofolio.keys():
            hist, _ = ambil_data_saham(ticker)
            ret = hist['Close'].pct_change().dropna()
            returns.append(ret)
        
        port_returns = pd.concat(returns, axis=1).mean(axis=1)
        market_returns = yf.Ticker("^JKSE").history(period="1y")['Close'].pct_change().dropna()
        
        covariance = np.cov(port_returns[-len(market_returns):], market_returns)[0][1]
        variance = np.var(market_returns)
        beta = covariance / variance
        
        st.sidebar.metric("Beta Portofolio", f"{beta:.2f}", 
                         "Lebih volatil" if beta > 1 else "Lebih stabil")
    except:
        pass

# Simulasi stress test
if st.sidebar.button("Stress Test"):
    with st.spinner("Menjalankan simulasi..."):
        try:
            scenarios = {
                'Resesi Ringan (-15%)': 0.85,
                'Krisis Global (-30%)': 0.70,
                'Pemulihan Ekonomi (+20%)': 1.20
            }
            
            results = []
            for scenario, multiplier in scenarios.items():
                nilai_baru = total_nilai * multiplier
                results.append((scenario, nilai_baru))
            
            st.subheader("Hasil Stress Test")
            for scenario, nilai in results:
                st.write(f"{scenario}: {format_rupiah(nilai)}")
                
            # Visualisasi
            fig, ax = plt.subplots()
            ax.barh([x[0] for x in results], [x[1] for x in results])
            ax.set_title("Dampak Berbagai Skenario")
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error dalam stress test: {str(e)}")
