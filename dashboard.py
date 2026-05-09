"""
dashboard.py
============
5G 信号质量监控看板 · Streamlit + pydeck 3D + Plotly
功能：
  - 侧边栏联动筛选（频段、终端类型、RSRP 范围）
  - pydeck ColumnLayer 3D 柱状地图（柱高 = 下载速率，颜色 = 信号强度）
  - 柱状图（各频段基站数量）& 环形饼图（终端类型占比）全部跟随筛选联动
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go

# ════════════════════════════════════════════════════════════
# 页面基础配置
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="5G 信号质量看板",
    page_icon="📡",
    layout="wide",
)

# ── 全局深色科技风样式 ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+SC:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans SC', sans-serif;
    background-color: #0a0e1a;
    color: #e0e8ff;
}
/* 侧边栏背景 */
section[data-testid="stSidebar"] {
    background: #0d1b2a;
    border-right: 1px solid #1e3a5f;
}
section[data-testid="stSidebar"] * { color: #c0d8f0 !important; }

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
    font-size: 2.4rem;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: -1px;
    margin: 0 0 8px 0;
    text-shadow: 0 0 30px rgba(0,212,255,0.4);
}
.hero-sub { font-size: 1rem; color: #7a9cc0; margin: 0; font-weight: 300; }

.kpi-row { display: flex; gap: 16px; margin-bottom: 28px; }
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
.legend { display: flex; gap: 20px; margin-bottom: 12px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 7px; font-size: 0.82rem; color: #a0b8d0; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 数据层：加载 & 特征工程
# ════════════════════════════════════════════════════════════

def classify_signal(rsrp: float) -> str:
    """
    根据 RSRP 值返回信号等级标签。

    分级标准（3GPP TS 38.133）：
        优秀 : RSRP > -90  dBm
        中等 : -110 <= RSRP <= -90  dBm
        较差 : RSRP < -110 dBm

    Args:
        rsrp: 参考信号接收功率，单位 dBm。

    Returns:
        信号等级字符串："优秀" | "中等" | "较差"
    """
    if rsrp > -90:
        return "优秀"
    elif rsrp >= -110:
        return "中等"
    else:
        return "较差"


def rsrp_to_color(rsrp: float) -> list[int]:
    """
    将 RSRP 值映射为 pydeck 所需的 RGBA 列表。

    颜色方案：
        绿色 [34, 197, 94]  → 优秀信号
        黄色 [250, 204, 21] → 中等信号
        红色 [239, 68, 68]  → 较差信号

    Args:
        rsrp: 参考信号接收功率，单位 dBm。

    Returns:
        长度为 4 的整数列表 [R, G, B, A]，A 固定为 200。
    """
    if rsrp > -90:
        return [34, 197, 94, 200]
    elif rsrp >= -110:
        return [250, 204, 21, 200]
    else:
        return [239, 68, 68, 200]


def normalize_elevation(series: pd.Series, scale: float = 800.0) -> pd.Series:
    """
    将下载速率归一化为 3D 柱高度（min-max 标准化后乘以缩放系数）。

    Args:
        series: 原始下载速率序列（Mbps）。
        scale:  最大柱高的像素倍率，默认 800。

    Returns:
        归一化后的高度序列（浮点数）。
    """
    min_v, max_v = series.min(), series.max()
    if max_v == min_v:          # 防止除零
        return pd.Series([scale / 2] * len(series), index=series.index)
    return (series - min_v) / (max_v - min_v) * scale


@st.cache_data
def load_data() -> pd.DataFrame:
    """
    从 CSV 读取原始采样数据并完成特征工程。

    新增列：
        signal_level : 信号等级文字标签
        color        : pydeck RGBA 颜色列表
        elevation    : 3D 柱高度（基于下载速率归一化）

    Returns:
        经过特征工程处理的 DataFrame。
    """
    df = pd.read_csv("signal_samples.csv")
    df["signal_level"] = df["RSRP_dBm"].apply(classify_signal)
    df["color"]        = df["RSRP_dBm"].apply(rsrp_to_color)
    df["elevation"]    = normalize_elevation(df["Download_Mbps"])
    return df


# ════════════════════════════════════════════════════════════
# 筛选层：根据侧边栏参数过滤数据
# ════════════════════════════════════════════════════════════

def apply_filters(
    df: pd.DataFrame,
    bands: list[str],
    terminals: list[str],
    rsrp_range: tuple[float, float],
) -> pd.DataFrame:
    """
    根据三类筛选条件返回过滤后的子集。

    Args:
        df:         原始 DataFrame。
        bands:      用户选中的频段列表，如 ["n28", "n41"]。
        terminals:  用户选中的终端类型列表。
        rsrp_range: RSRP 滑动条选中的 (最小值, 最大值) 元组，单位 dBm。

    Returns:
        满足所有条件的行子集（新 DataFrame，不修改原始数据）。
    """
    mask = (
        df["Band"].isin(bands) &
        df["TerminalType"].isin(terminals) &
        df["RSRP_dBm"].between(rsrp_range[0], rsrp_range[1])
    )
    return df[mask].copy()


# ════════════════════════════════════════════════════════════
# 图表构建层
# ════════════════════════════════════════════════════════════

# 统一 Plotly 暗色主题常量
_PLOT_BG  = "#0a0e1a"
_PAPER_BG = "#0f1e35"
_GRID_CLR = "#1e3a5f"
_TEXT_CLR = "#e0e8ff"
_TICK_CLR = "#7a9cc0"
_BAND_COLORS = {"n28": "#00d4ff", "n41": "#22c55e", "n78": "#f97316"}
_PIE_COLORS  = ["#00d4ff", "#22c55e", "#f97316"]


def build_bar_chart(df: pd.DataFrame) -> go.Figure:
    """
    构建"各频段唯一基站数量"柱状图。

    Args:
        df: 经筛选后的 DataFrame。

    Returns:
        Plotly Figure 对象。
    """
    band_counts = (
        df.groupby("Band")["CellID"]
        .nunique()
        .reset_index()
        .rename(columns={"CellID": "基站数量"})
        .sort_values("基站数量", ascending=False)
    )
    colors = [_BAND_COLORS.get(b, "#8888aa") for b in band_counts["Band"]]

    fig = go.Figure(go.Bar(
        x=band_counts["Band"],
        y=band_counts["基站数量"],
        marker_color=colors,
        marker_line_width=0,
        text=band_counts["基站数量"],
        textposition="outside",
        textfont=dict(color=_TEXT_CLR, family="Space Mono"),
    ))
    fig.update_layout(
        plot_bgcolor=_PLOT_BG,
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_CLR, family="Noto Sans SC"),
        xaxis=dict(title="", gridcolor=_GRID_CLR, tickfont=dict(color=_TICK_CLR, size=13)),
        yaxis=dict(title="基站数量（唯一 CellID）", gridcolor=_GRID_CLR, tickfont=dict(color=_TICK_CLR)),
        margin=dict(t=20, b=20, l=10, r=10),
        height=340,
        bargap=0.35,
    )
    return fig


def build_pie_chart(df: pd.DataFrame) -> go.Figure:
    """
    构建"终端类型占比"环形饼图。

    Args:
        df: 经筛选后的 DataFrame。

    Returns:
        Plotly Figure 对象。
    """
    term_counts = (
        df["TerminalType"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "TerminalType", "TerminalType": "数量", "count": "数量"})
    )
    fig = go.Figure(go.Pie(
        labels=term_counts.iloc[:, 0],
        values=term_counts.iloc[:, 1],
        hole=0.48,
        marker=dict(colors=_PIE_COLORS, line=dict(color=_PLOT_BG, width=3)),
        textfont=dict(size=13, color=_TEXT_CLR),
        hovertemplate="<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor=_PLOT_BG,
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_CLR, family="Noto Sans SC"),
        legend=dict(font=dict(color=_TEXT_CLR, size=12), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=20, b=20, l=10, r=10),
        height=340,
        annotations=[dict(
            text="终端<br>分布", x=0.5, y=0.5,
            font_size=14, font_color="#7a9cc0", showarrow=False,
        )],
    )
    return fig


def build_3d_map(df: pd.DataFrame) -> pdk.Deck:
    """
    构建 pydeck ColumnLayer 3D 柱状地图。

    柱体设计：
        - 高度（elevation）：由下载速率归一化决定，速率越高柱越高
        - 颜色（color）    ：由 RSRP 决定（绿/黄/红）
        - Tooltip          ：悬停显示基站编号、频段、RSRP、下载速率

    使用 carto-basemap 暗色底图，无需 Mapbox Token。

    Args:
        df: 经筛选后的 DataFrame，必须包含 elevation、color 列。

    Returns:
        pdk.Deck 对象，可直接传给 st.pydeck_chart()。
    """
    # 重新对筛选后子集做归一化，保证柱高相对分布正确
    df = df.copy()
    df["elevation"] = normalize_elevation(df["Download_Mbps"])

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["Longitude", "Latitude"],
        get_elevation="elevation",
        elevation_scale=1,
        radius=40,                      # 柱体底面半径（米）
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
        extruded=True,                  # 开启 3D 挤出效果
    )

    view = pdk.ViewState(
        latitude=df["Latitude"].mean(),
        longitude=df["Longitude"].mean(),
        zoom=13,
        pitch=50,                       # 俯仰角，50° 呈现明显 3D 透视
        bearing=-10,                    # 轻微旋转，增强立体感
    )

    tooltip = {
        "html": """
        <div style="background:#0f1e35;border:1px solid #1e3a5f;border-radius:8px;
                    padding:12px;font-family:monospace;font-size:12px;color:#e0e8ff">
          <b style="color:#00d4ff">基站 {CellID}</b><br/>
          📶 频段：{Band}<br/>
          📡 RSRP：<b>{RSRP_dBm} dBm</b><br/>
          🔊 SINR：{SINR_dB} dB<br/>
          📱 终端：{TerminalType}<br/>
          ⬇️ 下载：{Download_Mbps} Mbps<br/>
          📶 信号：{signal_level}
        </div>""",
        "style": {"background": "transparent", "border": "none"},
    }

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    )


# ════════════════════════════════════════════════════════════
# 主渲染逻辑
# ════════════════════════════════════════════════════════════

# 加载原始数据
df_all = load_data()

# ── 侧边栏筛选器 ───────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ 数据筛选")
    st.markdown("---")

    # 频段多选
    all_bands = sorted(df_all["Band"].unique().tolist())
    sel_bands = st.multiselect(
        "📶 频段",
        options=all_bands,
        default=all_bands,
        help="可多选，取消勾选即可从地图和图表中移除该频段",
    )

    st.markdown(" ")

    # 终端类型多选
    all_terminals = sorted(df_all["TerminalType"].unique().tolist())
    sel_terminals = st.multiselect(
        "📱 终端类型",
        options=all_terminals,
        default=all_terminals,
    )

    st.markdown(" ")

    # RSRP 范围滑动条
    rsrp_min = int(df_all["RSRP_dBm"].min())
    rsrp_max = int(df_all["RSRP_dBm"].max())
    sel_rsrp = st.slider(
        "📡 RSRP 范围（dBm）",
        min_value=rsrp_min,
        max_value=rsrp_max,
        value=(rsrp_min, rsrp_max),
        step=1,
        help="拖动两端滑块筛选信号强度范围",
    )

    st.markdown("---")
    st.caption("筛选器变更后地图与图表实时更新")

# ── 应用筛选 ───────────────────────────────────────────────
# 若用户取消了所有选项，给出提示，避免空数据渲染报错
if not sel_bands or not sel_terminals:
    st.warning("⚠️ 请至少选择一个频段和一种终端类型")
    st.stop()

df = apply_filters(df_all, sel_bands, sel_terminals, sel_rsrp)

if df.empty:
    st.warning("⚠️ 当前筛选条件下无数据，请调整侧边栏参数")
    st.stop()

# ── 大标题 ─────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <p class="hero-title">📡 5G 信号质量监控看板</p>
  <p class="hero-sub">Signal Intelligence Dashboard · 上海区域 · NR 5G · 实时采样分析</p>
</div>
""", unsafe_allow_html=True)

# ── KPI 卡片（基于筛选后数据） ─────────────────────────────
total  = len(df)
good   = (df["RSRP_dBm"] > -90).sum()
bad    = (df["RSRP_dBm"] < -110).sum()
avg_dl = df["Download_Mbps"].mean()

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value">{total}</div>
    <div class="kpi-label">筛选点数</div>
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

# ── 3D 地图 ────────────────────────────────────────────────
st.markdown('<p class="section-title">▍3D 地理分布 · 柱高 = 下载速率，颜色 = 信号强度</p>',
            unsafe_allow_html=True)

st.markdown("""
<div class="legend">
  <div class="legend-item"><span class="legend-dot" style="background:#22c55e"></span>优秀 RSRP &gt; -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#facc15"></span>中等 -110 ~ -90 dBm</div>
  <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>较差 RSRP &lt; -110 dBm</div>
  <div class="legend-item" style="color:#7a9cc0">｜ 柱越高 = 下载速率越快</div>
</div>
""", unsafe_allow_html=True)

st.pydeck_chart(build_3d_map(df), use_container_width=True, height=520)

st.divider()

# ── 图表区（联动筛选） ─────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<p class="section-title">▍各频段基站数量</p>', unsafe_allow_html=True)
    st.plotly_chart(build_bar_chart(df), use_container_width=True)

with col2:
    st.markdown('<p class="section-title">▍终端类型占比</p>', unsafe_allow_html=True)
    st.plotly_chart(build_pie_chart(df), use_container_width=True)

# ── 底部说明 ───────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;color:#2d4a6a;font-size:0.75rem;margin-top:24px;font-family:monospace;">
  5G NR · 频段 n28 / n41 / n78 · 数据来源: signal_samples.csv ·
  当前显示 {total} / {len(df_all)} 条 · 底图 © CARTO Dark Matter
</div>
""", unsafe_allow_html=True)
