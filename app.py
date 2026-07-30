import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Sales Dashboard", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# 2. Memuat Data & Pre-processing
@st.cache_data
def load_data():
    df = pd.read_excel("Data_Dummy_10000_Row.xlsx")
    df['Date'] = pd.to_datetime(df['Date'])
    df['Bulan-Tahun'] = df['Date'].dt.to_period('M').astype(str)
    
    # --- FITUR BARU: DEMOGRAFI GENERASI ---
    df['Tanggal Lahir'] = pd.to_datetime(df['Tanggal Lahir'])
    df['Tahun Lahir'] = df['Tanggal Lahir'].dt.year
    # Menghitung umur berdasarkan tahun transaksi terakhir
    tahun_sekarang = df['Date'].dt.year.max() 
    df['Umur'] = tahun_sekarang - df['Tahun Lahir']
    
    # Fungsi pengelompokan generasi
    def get_generation(year):
        if year >= 2013: return "Gen Alpha"
        elif year >= 1997: return "Gen Z"
        elif year >= 1981: return "Millennials"
        elif year >= 1965: return "Gen X"
        else: return "Baby Boomers"
        
    df['Generasi'] = df['Tahun Lahir'].apply(get_generation)
    return df

try:
    df = load_data()
    
    # 3. SIDEBAR: Filter Interaktif
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=100)
    st.sidebar.header("🔍 Filter Data")

    min_date = df['Date'].min()
    max_date = df['Date'].max()
    date_range = st.sidebar.date_input("Rentang Waktu", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    channels = st.sidebar.multiselect("Pilih Channel", options=df['Channel'].unique(), default=df['Channel'].unique())
    lokasi = st.sidebar.multiselect("Pilih Lokasi", options=df['Lokasi'].unique(), default=df['Lokasi'].unique())
    salesmen = st.sidebar.multiselect("Pilih Salesmen", options=df['Salesmen'].unique(), default=df['Salesmen'].unique())

    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (
            (df['Date'] >= pd.to_datetime(start_date)) &
            (df['Date'] <= pd.to_datetime(end_date)) &
            (df['Channel'].isin(channels)) &
            (df['Lokasi'].isin(lokasi)) &
            (df['Salesmen'].isin(salesmen))
        )
        filtered_df = df[mask]
    else:
        filtered_df = df

    # 4. KONTEN UTAMA
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("📈 Sales Dashboard - Advance")
    st.markdown("Dashboard interaktif untuk memonitor performa penjualan, wilayah, tren, dan pencapaian tim sales.")

    if filtered_df.empty:
        st.warning("Tidak ada data yang cocok dengan filter yang dipilih.")
    else:
        # MEMBAGI KONTEN MENJADI 3 TAB
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard Utama", "🔮 Prediksi Penjualan", "🧠 Advanced Analytics"])

        # ==========================================
        # ISI TAB 1: DASHBOARD UTAMA
        # ==========================================
        with tab1:
            st.markdown("### 📊 Key Performance Indicators")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total Pesanan", f"{len(filtered_df):,}")
            col2.metric("Total Barang Terjual", f"{filtered_df['QTY'].sum():,}")
            col3.metric("Total Nett Sales", f"Rp {filtered_df['Nett Sales'].sum():,.0f}")
            col4.metric("Total Gross Profit", f"Rp {filtered_df['Gross Profit'].sum():,.0f}")
            
            st.divider()

            col_trend, col_prod = st.columns([2, 1])
            with col_trend:
                if len(date_range) == 2 and (date_range[1] - date_range[0]).days <= 60:
                    trend_data = filtered_df.groupby("Date")["Nett Sales"].sum().reset_index()
                    x_kolom = "Date"
                    judul_grafik = "Tren Penjualan Harian (Nett Sales)"
                else:
                    trend_data = filtered_df.groupby("Bulan-Tahun")["Nett Sales"].sum().reset_index()
                    trend_data['Bulan-Tahun'] = pd.to_datetime(trend_data['Bulan-Tahun'])
                    trend_data = trend_data.sort_values('Bulan-Tahun')
                    trend_data['Bulan-Tahun'] = trend_data['Bulan-Tahun'].dt.strftime('%Y-%m')
                    x_kolom = "Bulan-Tahun"
                    judul_grafik = "Tren Penjualan Bulanan (Nett Sales)"
                
                fig_trend = px.line(trend_data, x=x_kolom, y="Nett Sales", markers=True, title=judul_grafik, line_shape="spline")
                fig_trend.update_layout(yaxis_rangemode='tozero')
                if len(trend_data) == 1:
                    fig_trend.update_traces(mode='markers', marker=dict(size=10))
                st.plotly_chart(fig_trend, use_container_width=True)
                
            with col_prod:
                top_products = filtered_df.groupby("Nama Barang")["QTY"].sum().nlargest(5).reset_index()
                fig_prod = px.bar(top_products, x="QTY", y="Nama Barang", orientation='h', title="Top 5 Produk Terlaris", color="Nama Barang")
                fig_prod.update_layout(showlegend=False)
                st.plotly_chart(fig_prod, use_container_width=True)

            col_sales, col_channel = st.columns([1, 1])
            with col_sales:
                sales_perf = filtered_df.groupby("Salesmen")[["Nett Sales", "Gross Profit"]].sum().reset_index()
                sales_perf = sales_perf.sort_values(by="Gross Profit", ascending=False)
                fig_sales = px.bar(sales_perf, x="Salesmen", y=["Gross Profit", "Nett Sales"], barmode="group", title="Performa Salesmen (Profit vs Sales)")
                st.plotly_chart(fig_sales, use_container_width=True)

            with col_channel:
                channel_dist = filtered_df.groupby("Channel")["Nett Sales"].sum().reset_index()
                fig_channel = px.pie(channel_dist, names="Channel", values="Nett Sales", hole=0.4, title="Kontribusi Channel Penjualan")
                st.plotly_chart(fig_channel, use_container_width=True)
                
            st.divider()
            
            st.markdown("### 🗺️ Analisa Wilayah Penjualan")
            col_loc1, col_loc2 = st.columns([2, 1])
            with col_loc1:
                loc_data = filtered_df.groupby("Lokasi")["Nett Sales"].sum().reset_index()
                loc_data = loc_data.sort_values(by="Nett Sales", ascending=True) 
                fig_loc = px.bar(loc_data, x="Nett Sales", y="Lokasi", orientation='h', title="Pendapatan Tertinggi Berdasarkan Lokasi", color="Nett Sales", color_continuous_scale="Viridis")
                st.plotly_chart(fig_loc, use_container_width=True)

            with col_loc2:
                loc_qty = filtered_df.groupby("Lokasi")["QTY"].sum().reset_index()
                fig_loc_pie = px.pie(loc_qty, names="Lokasi", values="QTY", hole=0.4, title="Distribusi Barang Terjual per Lokasi")
                st.plotly_chart(fig_loc_pie, use_container_width=True)

            st.divider()

            with st.expander("Tampilkan Detail Data Transaksi (Tabel)"):
                st.dataframe(filtered_df.sort_values(by="Date", ascending=False).head(500))

            st.markdown("### 📥 Unduh Laporan")
            st.caption("Unduh data transaksi yang telah Anda filter di atas ke dalam format CSV.")
            
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8')

            csv_data = convert_df(filtered_df)
            st.download_button(label="Download Data Filtered (CSV)", data=csv_data, file_name='laporan_sales_filtered.csv', mime='text/csv')

        # ==========================================
        # ISI TAB 2: PREDIKSI (FORECASTING)
        # ==========================================
        with tab2:
            st.header("🔮 Prediksi Penjualan (30 Hari ke Depan)")
            st.markdown("Menggunakan algoritma Machine Learning **Holt-Winters (Exponential Smoothing)** untuk memprediksi tren penjualan.")
            
            ts_data = filtered_df.groupby('Date')['Nett Sales'].sum().reset_index()
            if len(ts_data) >= 30:
                try:
                    ts_data = ts_data.set_index('Date').asfreq('D')
                    ts_data['Nett Sales'] = ts_data['Nett Sales'].fillna(0)
                    
                    model = ExponentialSmoothing(ts_data['Nett Sales'], trend='add', seasonal=None, initialization_method="estimated")
                    fit_model = model.fit()
                    forecast_steps = 30
                    forecast = fit_model.forecast(forecast_steps)
                    
                    history_df = ts_data.reset_index()
                    history_df['Tipe'] = 'Data Historis'
                    last_date = history_df['Date'].max()
                    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_steps)
                    
                    forecast_df = pd.DataFrame({'Date': forecast_dates, 'Nett Sales': forecast.values, 'Tipe': 'Prediksi (Forecast)'})
                    combined_df = pd.concat([history_df, forecast_df])
                    
                    fig_forecast = px.line(combined_df, x='Date', y='Nett Sales', color='Tipe', title="Grafik Historis & Prediksi Penjualan", color_discrete_map={'Data Historis': '#2E86C1', 'Prediksi (Forecast)': '#E74C3C'})
                    fig_forecast.update_layout(xaxis_title="Tanggal", yaxis_title="Total Penjualan (Rp)")
                    fig_forecast.add_vline(x=last_date, line_dash="dash", line_color="gray", annotation_text="Mulai Prediksi")
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    
                    st.subheader("💡 Ringkasan Prediksi Bulan Depan")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1: st.metric("Total Prediksi Penjualan", f"Rp {forecast.sum():,.0f}")
                    with col_f2: st.metric("Rata-rata Harian", f"Rp {forecast.mean():,.0f}")
                    with col_f3:
                        tren_status = "Naik 📈" if forecast.iloc[-1] > forecast.iloc[0] else "Turun 📉"
                        st.metric("Tren 30 Hari Kedepan", tren_status)
                        
                except Exception as e:
                    st.error(f"⚠️ Gagal melakukan prediksi. Detail error: {e}")
            else:
                st.warning("⚠️ Data historis yang dipilih kurang dari 30 hari. Silakan perlebar rentang waktu pada sidebar.")

        # ==========================================
        # ISI TAB 3: ADVANCED ANALYTICS (RFM & MARKET BASKET)
        # ==========================================
        with tab3:
            st.header("🧠 Advanced Analytics")
            st.markdown("Menggali *insight* tersembunyi mengenai perilaku pelanggan (*Customer Behavior*) menggunakan teknik *data science*.")
            
            # --- 1. RFM ANALYSIS ---
            st.subheader("1. Segmentasi Pelanggan (RFM Analysis)")
            st.caption("Mengelompokkan pelanggan berdasarkan kapan terakhir beli (Recency), seberapa sering (Frequency), dan total nilai belanja (Monetary).")
            
            max_date_rfm = filtered_df['Date'].max()
            rfm = filtered_df.groupby('Pelanggan').agg({
                'Date': lambda x: (max_date_rfm - x.max()).days,
                'No Pesanan': 'count',
                'Nett Sales': 'sum'
            }).reset_index()
            
            rfm.columns = ['Pelanggan', 'Recency (Hari)', 'Frequency (Trx)', 'Monetary (Rp)']
            
            f_med = rfm['Frequency (Trx)'].median()
            m_med = rfm['Monetary (Rp)'].median()
            
            def segment_customer(row):
                if row['Frequency (Trx)'] >= f_med and row['Monetary (Rp)'] >= m_med:
                    return "🌟 Loyal Customers"
                elif row['Recency (Hari)'] < 30:
                    return "👋 Active/New Customers"
                else:
                    return "⚠️ At Risk"
                    
            rfm['Segment'] = rfm.apply(segment_customer, axis=1)
            
            col_rfm1, col_rfm2 = st.columns([2, 1])
            with col_rfm1:
                # 3D/2D Scatter Plot
                fig_rfm = px.scatter(rfm, x='Recency (Hari)', y='Monetary (Rp)', size='Frequency (Trx)', color='Segment',
                                     hover_name='Pelanggan', title="Peta Persebaran Segmentasi Pelanggan")
                # Dibalik karena Recency angka kecil (0 hari) itu lebih bagus
                fig_rfm.update_layout(xaxis=dict(autorange="reversed")) 
                st.plotly_chart(fig_rfm, use_container_width=True)
                
            with col_rfm2:
                st.write("🏆 Top 10 Pelanggan VIP")
                st.dataframe(rfm[['Pelanggan', 'Monetary (Rp)', 'Segment']].sort_values('Monetary (Rp)', ascending=False).head(10))

            st.divider()

            # --- 2. MARKET BASKET ANALYSIS ---
            st.subheader("2. Market Basket Analysis (Product Affinity)")
            st.caption("Menemukan pola kombinasi barang yang paling sering dibeli oleh pelanggan yang sama (Rekomendasi Cross-Selling).")
            
            # Membuat Co-occurrence Matrix tanpa library mlxtend agar ringan
            basket = pd.crosstab(filtered_df['Pelanggan'], filtered_df['Nama Barang']).astype(bool).astype(int)
            co_matrix = basket.T.dot(basket)
            
            # --- PERBAIKAN ERROR BACA/TULIS (READ-ONLY) ---
            matrix_vals = co_matrix.to_numpy(copy=True)
            np.fill_diagonal(matrix_vals, 0)
            co_matrix = pd.DataFrame(matrix_vals, index=co_matrix.index, columns=co_matrix.columns)
            # ----------------------------------------------
            
            co_matrix.index.name = None
            co_matrix.columns.name = None
            pairs = co_matrix.unstack().reset_index()
            pairs.columns = ['Produk_A', 'Produk_B', 'Frekuensi']
            
            # Hapus kombinasi terbalik (A-B dan B-A)
            pairs = pairs[pairs['Produk_A'] < pairs['Produk_B']]
            pairs = pairs[pairs['Frekuensi'] > 0]
            pairs = pairs.sort_values(by='Frekuensi', ascending=False)
            
            if not pairs.empty:
                pairs['Kombinasi Rekomendasi'] = pairs['Produk_A'] + "  ➕  " + pairs['Produk_B']
                fig_basket = px.bar(pairs.head(10), x='Frekuensi', y='Kombinasi Rekomendasi', orientation='h',
                                    title="Top Kombinasi Barang (Sering Dibeli Bersamaan)",
                                    color='Frekuensi', color_continuous_scale='Sunset')
                fig_basket.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_basket, use_container_width=True)
            else:
                st.info("Data belum cukup untuk menemukan pola kombinasi Market Basket.")

            # --- 3. DEMOGRAFI PELANGGAN (GENERASI UMUR) ---
            st.divider()
            st.subheader("3. Segmentasi Demografi (Generasi Usia)")
            st.caption("Menganalisa daya beli dan preferensi produk berdasarkan rentang usia untuk strategi Marketing Campaign.")
            
            col_demo1, col_demo2 = st.columns(2)
            with col_demo1:
                # Grafik Pendapatan per Generasi (Donut Chart)
                gen_sales = filtered_df.groupby("Generasi")["Nett Sales"].sum().reset_index()
                fig_gen = px.pie(gen_sales, names="Generasi", values="Nett Sales", hole=0.4, 
                                 title="Kontribusi Pendapatan per Generasi",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_gen, use_container_width=True)
                
            with col_demo2:
                # Grafik Preferensi Produk per Generasi (Bar Chart Berkelompok)
                gen_prod = filtered_df.groupby(["Generasi", "Nama Barang"])["QTY"].sum().reset_index()
                fig_gen_prod = px.bar(gen_prod, x="Generasi", y="QTY", color="Nama Barang", 
                                      title="Preferensi Produk per Generasi", barmode="group")
                st.plotly_chart(fig_gen_prod, use_container_width=True)

        # G. FOOTER / KONTAK
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("---") 
        
        st.markdown("""
<div style="text-align: center; padding: 20px;">
<h4>Let's Connect! 🤝</h4>
<p>Dashboard ini dikembangkan oleh <strong>Saripudin Sahardi</strong></p>
<p style="color: gray; font-size: 14px;">Data Enthusiast | Tangerang Selatan, Indonesia</p>
<div style="margin-top: 15px;">
<a href="mailto:saripudinsahardi@gmail.com" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/732/732200.png" width="30" alt="Email" title="Kirim Email">
</a>
<a href="https://www.linkedin.com/in/saripudin-sahardi-387b74156/" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/3536/3536505.png" width="30" alt="LinkedIn" title="Kunjungi LinkedIn">
</a>
<a href="https://greenbird90.github.io/cvsaripudin/" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/3214/3214736.png" width="30" alt="Website" title="Kunjungi Portfolio">
</a>
</div>
</div>
        """, unsafe_allow_html=True)
            
except FileNotFoundError:
    st.error("File 'Data_Dummy_10000_Row.xlsx' tidak ditemukan.")