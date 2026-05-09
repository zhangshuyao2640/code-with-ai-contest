import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="5G 信号质量看板",
    page_icon="📡",
    layout="wide",
)

# ── 全局样式 ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+SC:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans SC', sans-serif;
    background-color: #0a0e1a;
    color: #e0e8ff;
}
.hero {
    background: linear-gradient(135deg, #0d1b2a 0%, #112240 60%, #0a192f 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 36px 48px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -40%; right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(0,200,255,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.6rem;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: -1px;
    margin: 0 0 8px 0;
    text-shadow: 0 0 30px rgba(0,212,255,0.4);
}
.hero-sub {
    font-size: 1rem;
    color: #7a9cc0;
    margin: 0;
    font-weight: 300;
}
.kpi-row {
    display: flex;
    gap: 16px;
    margin-bottom: 28px;
}
.kpi-card {
    flex: 1;
    background: #0f1e35;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
}
.kpi-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #00d4ff;
}
.kpi-label {
    font-size: 0.8rem;
    color: #7a9cc0;
    margin-top: 4px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 1rem;
    color: #00d4ff;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin: 0 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e3a5f;
}
.legend {
    display: flex;
    gap: 20px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 0.82rem;
    color: #a0b8d0;
}
.legend-dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ── 数据加载 ───────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("signal_samples.csv")

    def classify(rsrp):
        if rsrp > -90:
            return "优秀"
        elif rsrp >= -110:
            return "中等"
        else:
            return "较差"

    def color_hex(rsrp):
        if rsrp > -90:
            return "#22c55e"
        elif rsrp >= -110:
            return "#facc15"
        else:
            return "#ef4444"

    df["signal_level"] = df["RSRP_dBm"].apply(classify)
    df["color_hex"]    = df["RSRP_dBm"].apply(color_hex)
    return df

df = load_data()

# ── 大标题 ─────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <p class="hero-title">📡 5G 信号质量监控看板</p>
  <p class="hero-sub">Signal Intelligence Dashboard · 上海区域 · NR 5G · 实时采样分析</p>
</div>
""", unsafe_allow_html=True)

# ── KPI 卡片 ───────────────────────────────────────────────
total  = len(df)
good   = (df["RSRP_dBm"] > -90).sum()
bad    = (df["RSRP_dBm"] < -110).sum()
avg_dl = df["Download_Mbps"].mean()

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value">{total}</div>
    <div class="kpi-label">采样总点数</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:#22c55e">{good}</div>
    <div class="kpi-label">信号优秀点</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:#ef4444">{bad}</div>
    <div class="kpi-label">信号较差点</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:#facc15">{avg_dl:.1f}</div>
    <div class="kpi-label">平均下载速率 Mbps</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 真实地图（Folium + OpenStreetMap） ─────────────────────
st.markdown('<p class="section-title">▍地理分布 · 信号强度热图</p>', unsafe_allow_html=True)

st.markdown("""
<div class="legend">
  <div class="legend-item"><span class="legend-dot" style="background:#22c55e"></span>优秀 RSRP &gt; -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#facc15"></span>中等 -110 ~ -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>较差 RSRP &lt; -110 dBm</div>
</div>
""", unsafe_allow_html=True)

center_lat = df["Latitude"].mean()
center_lon = df["Longitude"].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=13,
    tiles="OpenStreetMap",
)

for _, row in df.iterrows():
    popup_html = f"""
    <div style="font-family:monospace;font-size:12px;min-width:180px">
      <b>基站 {row['CellID']}</b><br/>
      📶 频段：{row['Band']}<br/>
      📡 RSRP：<b>{row['RSRP_dBm']} dBm</b><br/>
      🔊 SINR：{row['SINR_dB']} dB<br/>
      📱 终端：{row['TerminalType']}<br/>
      ⬇️ 下载：{row['Download_Mbps']} Mbps<br/>
      📶 信号：{row['signal_level']}
    </div>
    """
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color=row["color_hex"],
        fill=True,
        fill_color=row["color_hex"],
        fill_opacity=0.85,
        weight=1.5,
        popup=folium.Popup(popup_html, max_width=220),
        tooltip=f"基站 {row['CellID']} | {row['RSRP_dBm']} dBm | {row['signal_level']}",
    ).add_to(m)

st_folium(m, use_container_width=True, height=500)

st.divider()

# ── 图表区 ─────────────────────────────────────────────────
col1, col2 = st.columns(2)

PLOT_BG  = "#0a0e1a"
PAPER_BG = "#0f1e35"
GRID_CLR = "#1e3a5f"
TEXT_CLR = "#e0e8ff"
TICK_CLR = "#7a9cc0"

with col1:
    st.markdown('<p class="section-title">▍各频段基站数量</p>', unsafe_allow_html=True)
    band_counts = df.groupby("Band")["CellID"].nunique().reset_index()
    band_counts.columns = ["Band", "基站数量"]
    band_counts = band_counts.sort_values("基站数量", ascending=False)

    BAND_COLORS = {"n28": "#00d4ff", "n41": "#22c55e", "n78": "#f97316"}
    colors = [BAND_COLORS.get(b, "#8888aa") for b in band_counts["Band"]]

    fig_bar = go.Figure(go.Bar(
        x=band_counts["Band"],
        y=band_counts["基站数量"],
        marker_color=colors,
        marker_line_width=0,
        text=band_counts["基站数量"],
        textposition="outside",
        textfont=dict(color=TEXT_CLR, family="Space Mono"),
    ))
    fig_bar.update_layout(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=TEXT_CLR, family="Noto Sans SC"),
        xaxis=dict(title="", gridcolor=GRID_CLR, tickfont=dict(color=TICK_CLR, size=13)),
        yaxis=dict(title="基站数量（唯一 CellID）", gridcolor=GRID_CLR, tickfont=dict(color=TICK_CLR)),
        margin=dict(t=20, b=20, l=10, r=10),
        height=340,
        bargap=0.35,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.markdown('<p class="section-title">▍终端类型占比</p>', unsafe_allow_html=True)
    term_counts = df["TerminalType"].value_counts().reset_index()
    term_counts.columns = ["TerminalType", "数量"]

    PIE_COLORS = ["#00d4ff", "#22c55e", "#f97316"]
    fig_pie = go.Figure(go.Pie(
        labels=term_counts["TerminalType"],
        values=term_counts["数量"],
        hole=0.48,
        marker=dict(colors=PIE_COLORS, line=dict(color=PLOT_BG, width=3)),
        textfont=dict(size=13, color=TEXT_CLR),
        hovertemplate="<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=TEXT_CLR, family="Noto Sans SC"),
        legend=dict(font=dict(color=TEXT_CLR, size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=20, b=20, l=10, r=10),
        height=340,
        annotations=[dict(
            text="终端<br>分布",
            x=0.5, y=0.5,
            font_size=14,
            font_color="#7a9cc0",
            showarrow=False,
        )],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("""
<div style="text-align:center;color:#2d4a6a;font-size:0.75rem;margin-top:24px;font-family:monospace;">
  5G NR · 频段 n28 / n41 / n78 · 数据来源: signal_samples.csv · 共 500 条采样 · 地图 © OpenStreetMap
</div>
""", unsafe_allow_html=True)
