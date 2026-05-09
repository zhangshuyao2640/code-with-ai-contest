import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="5G 信号质量看板",
    page_icon="📡",
    layout="wide",
)

# ── 全局样式注入 ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+SC:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans SC', sans-serif;
    background-color: #0a0e1a;
    color: #e0e8ff;
}

/* 大标题区 */
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
    top: -40%;
    right: -10%;
    width: 400px;
    height: 400px;
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

/* KPI 卡片 */
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

/* 区块标题 */
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

/* 图例 */
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
    # 信号强度分级
    def classify(rsrp):
        if rsrp > -90:
            return "优秀 (> -90)"
        elif rsrp >= -110:
            return "中等 (-110 ~ -90)"
        else:
            return "较差 (< -110)"

    def color(rsrp):
        if rsrp > -90:
            return [34, 197, 94, 210]       # 绿
        elif rsrp >= -110:
            return [250, 204, 21, 210]      # 黄
        else:
            return [239, 68, 68, 210]       # 红

    df["signal_level"] = df["RSRP_dBm"].apply(classify)
    df["color"] = df["RSRP_dBm"].apply(color)
    df["radius"] = 60
    return df

df = load_data()

# ── 大标题 ─────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <p class="hero-title">📡 5G 信号质量监控看板</p>
  <p class="hero-sub">Signal Intelligence Dashboard · 上海区域 · NR 5G · 实时采样分析</p>
</div>
""", unsafe_allow_html=True)

# ── KPI 指标行 ─────────────────────────────────────────────
total = len(df)
good  = (df["RSRP_dBm"] > -90).sum()
bad   = (df["RSRP_dBm"] < -110).sum()
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

# ── 地图 ───────────────────────────────────────────────────
st.markdown('<p class="section-title">▍地理分布 · 信号强度热图</p>', unsafe_allow_html=True)

st.markdown("""
<div class="legend">
  <div class="legend-item"><span class="legend-dot" style="background:#22c55e"></span>优秀 RSRP &gt; -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#facc15"></span>中等 -110 ~ -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>较差 RSRP &lt; -110 dBm</div>
</div>
""", unsafe_allow_html=True)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position=["Longitude", "Latitude"],
    get_fill_color="color",
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
    highlight_color=[255, 255, 255, 80],
)

view = pdk.ViewState(
    latitude=df["Latitude"].mean(),
    longitude=df["Longitude"].mean(),
    zoom=12,
    pitch=35,
)

tooltip = {
    "html": """
    <div style="background:#0f1e35;border:1px solid #1e3a5f;border-radius:8px;padding:12px;font-family:monospace;font-size:12px;color:#e0e8ff">
      <b style="color:#00d4ff">基站 {CellID}</b><br/>
      📶 频段：{Band}<br/>
      📍 位置：{Latitude:.4f}, {Longitude:.4f}<br/>
      📡 RSRP：<b>{RSRP_dBm} dBm</b><br/>
      🔊 SINR：{SINR_dB} dB<br/>
      📱 终端：{TerminalType}<br/>
      ⬇️ 下载：{Download_Mbps} Mbps
    </div>""",
    "style": {"background": "transparent", "border": "none"},
}

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/dark-v10",
)

st.pydeck_chart(deck, use_container_width=True)

st.divider()

# ── 图表区（两列） ──────────────────────────────────────────
col1, col2 = st.columns(2)

PLOT_BG   = "#0a0e1a"
PAPER_BG  = "#0f1e35"
GRID_CLR  = "#1e3a5f"
TEXT_CLR  = "#e0e8ff"
TICK_CLR  = "#7a9cc0"

# 柱状图：各频段基站数量
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
        yaxis=dict(title="基站数量（唯一CellID）", gridcolor=GRID_CLR, tickfont=dict(color=TICK_CLR)),
        margin=dict(t=20, b=20, l=10, r=10),
        height=340,
        bargap=0.35,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# 饼图：终端类型占比
with col2:
    st.markdown('<p class="section-title">▍终端类型占比</p>', unsafe_allow_html=True)
    term_counts = df["TerminalType"].value_counts().reset_index()
    term_counts.columns = ["TerminalType", "数量"]

    PIE_COLORS = ["#00d4ff", "#22c55e", "#f97316", "#a855f7"]
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
        legend=dict(
            font=dict(color=TEXT_CLR, size=12),
            bgcolor="rgba(0,0,0,0)",
        ),
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

# ── 底部说明 ───────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;color:#2d4a6a;font-size:0.75rem;margin-top:24px;font-family:monospace;">
  5G NR · 频段 n28 / n41 / n78 · 数据来源: signal_samples.csv · 共 500 条采样
</div>
""", unsafe_allow_html=True)
