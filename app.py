import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Sales Dashboard", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# 2. Memuat Data & Pre-processing
@st.cache_data
def load_data():
    df = pd.read_excel("Data_Dummy_Winod_10000_Row.xlsx")
    # Konversi kolom Date menjadi tipe datetime agar bisa difilter berdasarkan waktu
    df['Date'] = pd.to_datetime(df['Date'])
    # Buat kolom Bulan-Tahun untuk grafik tren
    df['Bulan-Tahun'] = df['Date'].dt.to_period('M').astype(str)
    return df

try:
    df = load_data()
    
    # 3. SIDEBAR: Filter Interaktif
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=100)
    st.sidebar.header("🔍 Filter Data")

    # Filter Rentang Waktu
    min_date = df['Date'].min()
    max_date = df['Date'].max()
    date_range = st.sidebar.date_input("Rentang Waktu", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    # Filter Multi-select
    channels = st.sidebar.multiselect("Pilih Channel", options=df['Channel'].unique(), default=df['Channel'].unique())
    lokasi = st.sidebar.multiselect("Pilih Lokasi", options=df['Lokasi'].unique(), default=df['Lokasi'].unique())
    salesmen = st.sidebar.multiselect("Pilih Salesmen", options=df['Salesmen'].unique(), default=df['Salesmen'].unique())

    # Terapkan Filter ke Dataframe
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
    /* Mengecilkan ukuran font nilai angka pada metrik */
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
    }
    /* Opsional: Mengecilkan ukuran font label/judul metrik agar proporsional */
    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # ------------------------------

    st.title("📈 Sales Dashboard - Advance")
    st.markdown("Dashboard interaktif untuk memonitor performa penjualan, wilayah, tren, dan pencapaian tim sales.")

    # Tampilkan Peringatan jika data kosong setelah difilter
    if filtered_df.empty:
        st.warning("Tidak ada data yang cocok dengan filter yang dipilih.")
    else:
        # A. Key Performance Indicators (KPI) Dinamis
        st.markdown("### 📊 Key Performance Indicators")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Pesanan", f"{len(filtered_df):,}")
        col2.metric("Total Barang Terjual", f"{filtered_df['QTY'].sum():,}")
        col3.metric("Total Nett Sales", f"Rp {filtered_df['Nett Sales'].sum():,.0f}")
        col4.metric("Total Gross Profit", f"Rp {filtered_df['Gross Profit'].sum():,.0f}")
        
        st.divider()

        # B. GRAFIK BARIS 1: Tren Penjualan & Produk Terlaris
        col_trend, col_prod = st.columns([2, 1])

        with col_trend:
            # 1. Cek rentang hari dari filter
            if len(date_range) == 2 and (date_range[1] - date_range[0]).days <= 60:
                # Gunakan tren HARIAN jika rentang waktu <= 60 hari
                trend_data = filtered_df.groupby("Date")["Nett Sales"].sum().reset_index()
                x_kolom = "Date"
                judul_grafik = "Tren Penjualan Harian (Nett Sales)"
            else:
                # Gunakan tren BULANAN jika lebih dari 60 hari
                trend_data = filtered_df.groupby("Bulan-Tahun")["Nett Sales"].sum().reset_index()
                trend_data['Bulan-Tahun'] = pd.to_datetime(trend_data['Bulan-Tahun'])
                trend_data = trend_data.sort_values('Bulan-Tahun')
                trend_data['Bulan-Tahun'] = trend_data['Bulan-Tahun'].dt.strftime('%Y-%m')
                x_kolom = "Bulan-Tahun"
                judul_grafik = "Tren Penjualan Bulanan (Nett Sales)"
            
            # 2. Buat grafik
            fig_trend = px.line(trend_data, x=x_kolom, y="Nett Sales", markers=True,
                                title=judul_grafik,
                                line_shape="spline")
            
            # 3. Perbaiki skala Y agar selalu mulai dari 0 (mencegah zoom aneh)
            fig_trend.update_layout(yaxis_rangemode='tozero')
            
            # 4. Jika datanya kebetulan cuma 1 titik (misal difilter cuma 1 hari)
            if len(trend_data) == 1:
                fig_trend.update_traces(mode='markers', marker=dict(size=10))

            st.plotly_chart(fig_trend, use_container_width=True)
        with col_prod:
            # Grafik Produk Terlaris (Berdasarkan QTY)
            top_products = filtered_df.groupby("Nama Barang")["QTY"].sum().nlargest(5).reset_index()
            fig_prod = px.bar(top_products, x="QTY", y="Nama Barang", orientation='h',
                              title="Top 5 Produk Terlaris", color="Nama Barang")
            fig_prod.update_layout(showlegend=False)
            st.plotly_chart(fig_prod, use_container_width=True)

        # C. GRAFIK BARIS 2: Performa Salesmen & Distribusi Channel
        col_sales, col_channel = st.columns([1, 1])

        with col_sales:
            # Performa Salesmen (Berdasarkan Profit)
            sales_perf = filtered_df.groupby("Salesmen")[["Nett Sales", "Gross Profit"]].sum().reset_index()
            sales_perf = sales_perf.sort_values(by="Gross Profit", ascending=False)
            fig_sales = px.bar(sales_perf, x="Salesmen", y=["Gross Profit", "Nett Sales"], 
                               barmode="group", title="Performa Salesmen (Profit vs Sales)")
            st.plotly_chart(fig_sales, use_container_width=True)

        with col_channel:
            # Distribusi Channel
            channel_dist = filtered_df.groupby("Channel")["Nett Sales"].sum().reset_index()
            fig_channel = px.pie(channel_dist, names="Channel", values="Nett Sales", 
                                 hole=0.4, title="Kontribusi Channel Penjualan")
            st.plotly_chart(fig_channel, use_container_width=True)
            
        st.divider()
        
        # D. GRAFIK BARIS 3: Analisa Wilayah (Lokasi)
        st.markdown("### 🗺️ Analisa Wilayah Penjualan")
        col_loc1, col_loc2 = st.columns([2, 1])

        with col_loc1:
            # Grafik Pendapatan Berdasarkan Lokasi (Bar Chart Horizontal)
            loc_data = filtered_df.groupby("Lokasi")["Nett Sales"].sum().reset_index()
            loc_data = loc_data.sort_values(by="Nett Sales", ascending=True) 
            
            fig_loc = px.bar(loc_data, x="Nett Sales", y="Lokasi", orientation='h',
                             title="Pendapatan Tertinggi Berdasarkan Lokasi",
                             color="Nett Sales", color_continuous_scale="Viridis")
            st.plotly_chart(fig_loc, use_container_width=True)

        with col_loc2:
            # Proporsi Lokasi berdasarkan QTY Barang Terjual (Donut Chart)
            loc_qty = filtered_df.groupby("Lokasi")["QTY"].sum().reset_index()
            fig_loc_pie = px.pie(loc_qty, names="Lokasi", values="QTY", hole=0.4,
                                 title="Distribusi Barang Terjual per Lokasi")
            st.plotly_chart(fig_loc_pie, use_container_width=True)

        st.divider()

        # E. TABEL DATA MENTAH
        with st.expander("Tampilkan Detail Data Transaksi (Tabel)"):
            st.dataframe(filtered_df.sort_values(by="Date", ascending=False).head(500))

        # F. FUNGSI UNDUH LAPORAN
        st.markdown("### 📥 Unduh Laporan")
        st.caption("Unduh data transaksi yang telah Anda filter di atas ke dalam format CSV.")
        
        @st.cache_data
        def convert_df(df):
            # Mengubah dataframe menjadi format CSV
            return df.to_csv(index=False).encode('utf-8')

        csv_data = convert_df(filtered_df)
        
        st.download_button(
            label="Download Data Filtered (CSV)",
            data=csv_data,
            file_name='laporan_winod_filtered.csv',
            mime='text/csv',
        )

        st.markdown("<br><br>", unsafe_allow_html=True) # Memberikan jarak spasi
        st.markdown("---") # Garis pembatas
        
       # G. FOOTER / KONTAK (Untuk Recruiter)
        st.markdown("""
<div style="text-align: center; padding: 20px;">
<h4>Let's Connect! 🤝</h4>
<p>Dashboard ini dikembangkan oleh <strong>Saripudin Sahardi</strong></p>
<p style="color: gray; font-size: 14px;">Data Enthusiast | Tangerang Selatan, Indonesia</p>
<div style="margin-top: 15px;">
<!-- Link Email -->
<a href="mailto:saripudinsahardi@gmail.com" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/732/732200.png" width="30" alt="Email" title="Kirim Email">
</a>
<!-- Link LinkedIn -->
<a href="https://www.linkedin.com/in/saripudin-sahardi-387b74156/" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/174/174848.png" width="30" alt="LinkedIn" title="Kunjungi LinkedIn">
</a>
<!-- Link Website/Portfolio -->
<a href="https://greenbird90.github.io/cvsaripudin/" target="_blank" style="text-decoration: none; margin: 0 15px;">
<img src="https://cdn-icons-png.flaticon.com/512/3214/3214736.png" width="30" alt="Website" title="Kunjungi Portfolio">
</a>
</div>
</div>
        """, unsafe_allow_html=True)
            
except FileNotFoundError:
    st.error("File 'Data_Dummy_Winod_10000_Row.xlsx' tidak ditemukan. Pastikan file berada di folder yang sama dengan app.py.")
