import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ==================== 1. CONFIG ====================
st.set_page_config(
    page_title="Dashboard Analisis PKPU",
    page_icon="⚖️",
    layout="wide"
)

def normalize_sektor(x):
    if pd.isna(x):
        return x

    x = str(x).strip().lower()

    # hilangkan awalan L
    x = re.sub(r'^l\s+', '', x)

    return x.title()

# ==================== 2. LOAD & CLEAN DATA ====================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/13McAh50P4ZEHirNn_dHp1JpoywrnQ7bpsRNPToDjKhY/export?format=csv&gid=448442818"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    df['Tanggal Putusan'] = pd.to_datetime(df['Tanggal Putusan'], format='%d/%m/%Y', errors='coerce')
    df['Tahun'] = df['Tahun'].astype(int)
    df['Bulan'] = df['Tanggal Putusan'].dt.month
    df['Bulan_Nama'] = df['Tanggal Putusan'].dt.strftime('%b %Y')
    
    df['Sektor'] = df['Sektor'].apply(normalize_sektor)
    
    def parse_rupiah(val):
        if pd.isna(val) or val in ['-', '', 'Rp0', None]:
            return 0
        if isinstance(val, str):
            clean = re.sub(r'[^\d,]', '', val)
            clean = clean.replace(',', '.')
            try:
                return float(clean)
            except:
                return 0
        return val
    
    df['K_Separatis_num'] = df['K Separatis'].apply(parse_rupiah)
    df['K_Preferen_num'] = df['K Preferen'].apply(parse_rupiah)
    df['K_Konkuren_num'] = df['K Konkuren'].apply(parse_rupiah)
    
    df['Total_Tagihan'] = df['K_Separatis_num'] + df['K_Preferen_num'] + df['K_Konkuren_num']
    
    df['Tbk'] = df['Tbk'].fillna('Tidak Diketahui').str.strip()
    df['Disclosed'] = df['Disclosed'].fillna('Unknown').str.strip()
    
    return df

df = load_data()


# ==================== 3. SIDEBAR ====================
st.sidebar.header("🔍 Filter")

tahun_selected = st.sidebar.multiselect(
    "Pilih Tahun:",
    options=sorted(df['Tahun'].unique()),
    default=sorted(df['Tahun'].unique())
)

sektor_selected = st.sidebar.multiselect(
    "Pilih Sektor:",
    options=sorted(df['Sektor'].dropna().unique()),
    default=[]
)

pn_selected = st.sidebar.multiselect(
    "Pilih PN (Pengadilan Negeri):",
    options=sorted(df['PN'].dropna().unique()),
    default=[]
)

df_filtered = df[df['Tahun'].isin(tahun_selected)].copy()
if sektor_selected:
    df_filtered = df_filtered[df_filtered['Sektor'].isin(sektor_selected)]
if pn_selected:
    df_filtered = df_filtered[df_filtered['PN'].isin(pn_selected)]

# ==================== 4. HEADER & KPI ====================
st.title("Dashboard  Kasus PKPU")
st.markdown("**Analisis sektoral & geografis Putusan Penundaan Kewajiban Pembayaran Utang (PKPU) (2024-2026)**")
st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Kasus", f"{len(df_filtered):,}")
    
with col2:
    total_tagihan = df_filtered['Total_Tagihan'].sum()
    st.metric("Total Tagihan", f"Rp {total_tagihan/1e12:.2f} T")

with col3:
    n_sektor = df_filtered['Sektor'].nunique()
    st.metric("Sektor Terdampak", f"{n_sektor}")

with col4:
    n_tbk = (df_filtered['Tbk'] == 'Tbk').sum()
    st.metric("Perusahaan Tbk", f"{n_tbk}")

with col5:
    pct_disclosed = (df_filtered['Disclosed'] == 'Disclosed').sum() / max(len(df_filtered), 1) * 100
    st.metric("% Disclosed", f"{pct_disclosed:.1f}%")

st.markdown("---")

# ==================== 5. TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Analisis Sektor", "Peta Wilayah", "Nilai Utang", 
    "Tren Waktu", "Data Lengkap"
])

# ==================== TAB 1: ANALISIS SEKTOR ====================
with tab1:
    st.subheader("🎯 Sektor Mana Saja yang Paling Terdampak?")
    
    sektor_analysis = df_filtered.groupby('Sektor').agg(
        Jumlah_Kasus=('No', 'count'),
        Total_Tagihan=('Total_Tagihan', 'sum'),
        Rata_rata=('Total_Tagihan', 'mean'),
        Kasus_Tbk=('Tbk', lambda x: (x == 'Tbk').sum())
    ).reset_index().sort_values('Jumlah_Kasus', ascending=False)
    
    col_a, col_b = st.columns([3, 2])
    
    with col_a:
        fig_bar = px.bar(
            sektor_analysis.head(15),
            x='Jumlah_Kasus', y='Sektor',
            orientation='h',
            title='<b>Top 15 Sektor - Jumlah Kasus PKPU</b>',
            color='Jumlah_Kasus',
            color_continuous_scale='Reds',
            text='Jumlah_Kasus'
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=500,
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_b:
        fig_pie = px.pie(
            sektor_analysis.head(10),
            values='Jumlah_Kasus', names='Sektor',
            title='<b>Distribusi % Kasus per Sektor</b>',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        bubble_data = sektor_analysis.copy()
        bubble_data['Total_Tagihan_T'] = (
            bubble_data['Total_Tagihan'] / 1e12
        )
        bubble_data['Rata_Rata_M'] = (
            bubble_data['Rata_rata'] / 1e9
        )
    # ✅ PERBAIKAN: Hapus background_gradient
    st.subheader("Tabel Ranking Detail per Sektor")
    sektor_display = sektor_analysis.copy()
    sektor_display['Total_Tagihan_T'] = sektor_display['Total_Tagihan'] / 1e12
    sektor_display['Rata_rata_M'] = sektor_display['Rata_rata'] / 1e9
    sektor_display = sektor_display[['Sektor', 'Jumlah_Kasus', 'Total_Tagihan_T', 'Rata_rata_M', 'Kasus_Tbk']]
    sektor_display.columns = ['Sektor', 'Jumlah Kasus', 'Total Tagihan (T)', 'Rata-rata (M)', 'Kasus Tbk']
    
    # Format angka tanpa background_gradient
    st.dataframe(
        sektor_display.style.format({'Total Tagihan (T)': '{:.2f}', 'Rata-rata (M)': '{:.1f}'}),
        use_container_width=True, height=400
    )
    
    # Highlight top sektor dengan bar chart tambahan
    st.subheader("🏆 Top 10 Sektor - Total Tagihan (Triliun Rp)")
    top_tagihan = sektor_analysis.nlargest(10, 'Total_Tagihan')
    top_tagihan['Total_Tagihan_T'] = top_tagihan['Total_Tagihan'] / 1e12
    
    fig_top = px.bar(
        top_tagihan, x='Total_Tagihan_T', y='Sektor',
        orientation='h',
        color='Jumlah_Kasus',
        color_continuous_scale='Viridis',
        title='Top 10 Sektor berdasarkan Total Tagihan',
        text='Total_Tagihan_T'
    )
    fig_top.update_traces(texttemplate='Rp %{text:.2f}T', textposition='outside')
    fig_top.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500)
    st.plotly_chart(fig_top, use_container_width=True)
    
    top_sektor = sektor_analysis.iloc[0]
    st.info(
        f"💡 **Insight:** Sektor **{top_sektor['Sektor']}** adalah yang paling terdampak dengan "
        f"**{top_sektor['Jumlah_Kasus']} kasus** "
        f"dan total tagihan **Rp {top_sektor['Total_Tagihan']/1e12:.2f} Triliun**."
    )

# ==================== TAB 2: PETA WILAYAH ====================
with tab2:
    st.subheader("Distribusi Geografis Kasus PKPU")
    
    geo_analysis = df_filtered.groupby('PN').agg(
        Jumlah_Kasus=('No', 'count'),
        Total_Tagihan=('Total_Tagihan', 'sum')
    ).reset_index().sort_values('Jumlah_Kasus', ascending=False)
    
    col_c, col_d = st.columns(2)
    
    with col_c:
        fig_pn = px.bar(
            geo_analysis,
            x='Jumlah_Kasus', y='PN',
            orientation='h',
            title='<b>Jumlah Kasus per Pengadilan Negeri</b>',
            color='Total_Tagihan',
            color_continuous_scale='Viridis',
            text='Jumlah_Kasus'
        )
        fig_pn.update_traces(textposition='outside')
        fig_pn.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500)
        st.plotly_chart(fig_pn, use_container_width=True)
    
    with col_d:
        fig_bubble = px.scatter(
            bubble_data,
            x='Jumlah_Kasus',
            y='Total_Tagihan_T',
            size='Rata_Rata_M',
            color='Jumlah_Kasus',
            hover_name='Sektor',
            title='Peta Risiko Sektor PKPU',
            labels={
                'Jumlah_Kasus':'Jumlah Kasus',
                'Total_Tagihan_T':'Total Tagihan (T)'
            },
            size_max=60
        )

        fig_bubble.update_layout(height=600)

        st.plotly_chart(
            fig_bubble,
            use_container_width=True
        )
    
    st.subheader("Heatmap: Sektor vs Pengadilan Negeri")
    heatmap_data = df_filtered.groupby(['Sektor', 'PN']).size().reset_index(name='Jumlah')
    heatmap_pivot = heatmap_data.pivot(index='Sektor', columns='PN', values='Jumlah').fillna(0)
    
    fig_heatmap = px.imshow(
        heatmap_pivot,
        text_auto=True,
        aspect='auto',
        color_continuous_scale='YlOrRd',
        title='Heatmap Konsentrasi Kasus'
    )
    fig_heatmap.update_layout(height=500)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ==================== TAB 3: NILAI UTANG ====================
with tab3:
    st.subheader("Analisis Nilai Utang (Tagihan)")
    
    total_sep = df_filtered['K_Separatis_num'].sum()
    total_pref = df_filtered['K_Preferen_num'].sum()
    total_kon = df_filtered['K_Konkuren_num'].sum()
    
    col_e, col_f, col_g = st.columns(3)
    col_e.metric("Kreditur Separatis", f"Rp {total_sep/1e12:.2f} T")
    col_f.metric("Kreditur Preferen", f"Rp {total_pref/1e12:.2f} T")
    col_g.metric("Kreditur Konkuren", f"Rp {total_kon/1e12:.2f} T")
    
    st.subheader("Komposisi Tagihan per Sektor")
    setor_tagihan = df_filtered.groupby('Sektor').agg({
        'K_Separatis_num': 'sum',
        'K_Preferen_num': 'sum',
        'K_Konkuren_num': 'sum'
    }).reset_index()
    setor_tagihan['Total'] = setor_tagihan['K_Separatis_num'] + setor_tagihan['K_Preferen_num'] + setor_tagihan['K_Konkuren_num']
    setor_tagihan = setor_tagihan.sort_values('Total', ascending=True).tail(12)
    
    fig_stack = go.Figure()
    fig_stack.add_trace(go.Bar(name='Separatis', y=setor_tagihan['Sektor'], 
                                x=setor_tagihan['K_Separatis_num']/1e12, orientation='h',
                                marker_color='#1f77b4'))
    fig_stack.add_trace(go.Bar(name='Preferen', y=setor_tagihan['Sektor'], 
                                x=setor_tagihan['K_Preferen_num']/1e12, orientation='h',
                                marker_color='#ff7f0e'))
    fig_stack.add_trace(go.Bar(name='Konkuren', y=setor_tagihan['Sektor'], 
                                x=setor_tagihan['K_Konkuren_num']/1e12, orientation='h',
                                marker_color='#2ca02c'))
    
    fig_stack.update_layout(
        barmode='stack',
        title='Komposisi Tagihan (Triliun Rp) per Sektor',
        xaxis_title='Triliun Rp',
        height=500
    )
    st.plotly_chart(fig_stack, use_container_width=True)
    
    st.subheader("Top 20 Kasus dengan Tagihan Terbesar")
    top_cases = df_filtered.nlargest(20, 'Total_Tagihan')[
        ['Nama Debitur', 'Sektor', 'PN', 'Tahun', 'Total_Tagihan', 'Disclosed']
    ].copy()
    top_cases['Total_Tagihan_T'] = top_cases['Total_Tagihan'] / 1e12
    
    fig_top = px.bar(
        top_cases,
        x='Total_Tagihan_T', y='Nama Debitur',
        orientation='h',
        color='Sektor',
        title='Top 20 Kasus - Tagihan Terbesar',
        hover_data=['PN', 'Tahun', 'Disclosed']
    )
    fig_top.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=600
    )
    st.plotly_chart(fig_top, use_container_width=True)
    
    st.dataframe(
        top_cases[['Nama Debitur', 'Sektor', 'PN', 'Tahun', 'Total_Tagihan_T', 'Disclosed']]
        .rename(columns={'Total_Tagihan_T': 'Tagihan (T)'})
        .style.format({'Tagihan (T)': '{:.2f}'}),
        use_container_width=True
    )

# ==================== TAB 4: TREN WAKTU ====================
with tab4:
    st.subheader("Tren Kasus PKPU Sepanjang Waktu")
    
    yearly = df_filtered.groupby('Tahun').agg(
        Jumlah=('No', 'count'),
        Total=('Total_Tagihan', 'sum')
    ).reset_index()
    
    col_h, col_i = st.columns(2)
    
    with col_h:
        fig_year = px.line(
            yearly, x='Tahun', y='Jumlah',
            markers=True, title='Tren Jumlah Kasus per Tahun',
            text='Jumlah'
        )
        fig_year.update_traces(textposition='top center', line=dict(width=3, color='#E63946'))
        st.plotly_chart(fig_year, use_container_width=True)
    
    with col_i:
        fig_year_val = px.bar(
            yearly, x='Tahun', y='Total',
            title='Tren Total Tagihan per Tahun (Rp)',
            color='Total',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_year_val, use_container_width=True)
    
    st.subheader("Distribusi Kasus per Bulan")
    monthly = df_filtered.groupby([df_filtered['Tanggal Putusan'].dt.to_period('M')]).size().reset_index(name='Jumlah')
    monthly['Tanggal Putusan'] = monthly['Tanggal Putusan'].astype(str)
    
    fig_month = px.line(
        monthly, x='Tanggal Putusan', y='Jumlah',
        markers=True, title='Tren Kasus per Bulan'
    )
    fig_month.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig_month, use_container_width=True)
    
    st.subheader(" Evolusi Kasus per Sektor (Tren)")
    sektor_year = df_filtered.groupby(['Tahun', 'Sektor']).size().reset_index(name='Jumlah')
    
    fig_area = px.area(
        sektor_year, x='Tahun', y='Jumlah', color='Sektor',
        title='Komposisi Kasus per Sektor dari Waktu ke Waktu'
    )
    fig_area.update_layout(height=500)
    st.plotly_chart(fig_area, use_container_width=True)

# ==================== TAB 5: DATA LENGKAP ====================
with tab5:
    st.subheader("Data Lengkap Kasus PKPU")
    st.write(f"Menampilkan **{len(df_filtered)}** baris data")
    
    cols_show = st.multiselect(
        "Pilih kolom yang ditampilkan:",
        options=['No', 'Tanggal Putusan', 'Tahun', 'Nama Debitur', 'Sektor', 'PN', 
                 'Tbk', 'Disclosed', 'Total_Tagihan', 'K_Separatis_num', 
                 'K_Preferen_num', 'K_Konkuren_num'],
        default=['No', 'Tanggal Putusan', 'Nama Debitur', 'Sektor', 'PN', 'Total_Tagihan', 'Disclosed']
    )
    
    df_show = df_filtered[cols_show].copy() if cols_show else df_filtered
    
    money_cols = ['Total_Tagihan', 'K_Separatis_num', 'K_Preferen_num', 'K_Konkuren_num']
    for col in money_cols:
        if col in df_show.columns:
            df_show[col] = df_show[col].apply(lambda x: f"Rp {x:,.0f}" if x > 0 else "-")
    
    st.dataframe(df_show, use_container_width=True, height=500)
    
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Data (CSV)",
        data=csv,
        file_name='pkpu_filtered.csv',
        mime='text/csv'
    )

st.markdown("---")
st.caption(f"Dashboard dibuat dari {len(df)} kasus PKPU | Sumber: dataaa_pkpu - Sheet1.csv")
