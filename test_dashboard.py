"""
test_dashboard.py
=================
5G 看板核心逻辑单元测试
覆盖范围：数据加载/清洗、筛选过滤、图表构建函数

运行方式：
    pytest test_dashboard.py -v
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── 从 dashboard 导入被测函数 ──────────────────────────────
from dashboard import (
    classify_signal,
    rsrp_to_color,
    normalize_elevation,
    apply_filters,
    build_bar_chart,
    build_pie_chart,
)


# ════════════════════════════════════════════════════════════
# Fixtures：构造测试用 DataFrame
# ════════════════════════════════════════════════════════════

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """构造覆盖三种信号等级、三种频段、三种终端类型的最小测试数据集。"""
    return pd.DataFrame({
        "Latitude":      [31.20, 31.21, 31.22, 31.23, 31.24],
        "Longitude":     [121.45, 121.46, 121.47, 121.48, 121.49],
        "CellID":        [1001, 1002, 1003, 1001, 1004],
        "Band":          ["n28", "n41", "n78", "n28", "n41"],
        "RSRP_dBm":      [-85.0, -95.0, -115.0, -89.9, -110.1],
        "SINR_dB":       [20.0, 10.0, -3.0, 15.0, 5.0],
        "TerminalType":  ["Smartphone", "CPE", "IoT", "Smartphone", "CPE"],
        "Download_Mbps": [500.0, 200.0, 50.0, 800.0, 100.0],
    })


@pytest.fixture
def enriched_df(sample_df) -> pd.DataFrame:
    """在 sample_df 基础上添加 signal_level / color / elevation 列。"""
    df = sample_df.copy()
    df["signal_level"] = df["RSRP_dBm"].apply(classify_signal)
    df["color"]        = df["RSRP_dBm"].apply(rsrp_to_color)
    df["elevation"]    = normalize_elevation(df["Download_Mbps"])
    return df


# ════════════════════════════════════════════════════════════
# 1. classify_signal 单元测试
# ════════════════════════════════════════════════════════════

class TestClassifySignal:
    """测试 RSRP → 信号等级映射逻辑。"""

    def test_excellent_above_threshold(self):
        """RSRP > -90 应返回"优秀"。"""
        assert classify_signal(-85.0) == "优秀"

    def test_excellent_boundary(self):
        """RSRP = -89.9 仍属优秀（恰好大于 -90）。"""
        assert classify_signal(-89.9) == "优秀"

    def test_medium_lower_boundary(self):
        """RSRP = -110 恰在中等下边界（>= -110）。"""
        assert classify_signal(-110.0) == "中等"

    def test_medium_upper_boundary(self):
        """RSRP = -90 恰在中等上边界（<= -90）。"""
        assert classify_signal(-90.0) == "中等"

    def test_poor_below_threshold(self):
        """RSRP < -110 应返回"较差"。"""
        assert classify_signal(-115.0) == "较差"

    def test_poor_boundary(self):
        """RSRP = -110.1 刚越过下边界，应返回"较差"。"""
        assert classify_signal(-110.1) == "较差"

    @pytest.mark.parametrize("rsrp,expected", [
        (-70.0,  "优秀"),
        (-100.0, "中等"),
        (-120.0, "较差"),
    ])
    def test_parametrized(self, rsrp, expected):
        """参数化覆盖三个典型值。"""
        assert classify_signal(rsrp) == expected


# ════════════════════════════════════════════════════════════
# 2. rsrp_to_color 单元测试
# ════════════════════════════════════════════════════════════

class TestRsrpToColor:
    """测试 RSRP → RGBA 颜色映射。"""

    def test_excellent_is_green(self):
        """优秀信号应返回绿色 RGB。"""
        r, g, b, a = rsrp_to_color(-85.0)
        assert r < 100 and g > 150          # 绿色主导

    def test_medium_is_yellow(self):
        """中等信号应返回黄色 RGB。"""
        r, g, b, a = rsrp_to_color(-100.0)
        assert r > 200 and g > 150 and b < 100  # 红+绿 = 黄

    def test_poor_is_red(self):
        """较差信号应返回红色 RGB。"""
        r, g, b, a = rsrp_to_color(-115.0)
        assert r > 200 and g < 100          # 红色主导

    def test_returns_list_of_4(self):
        """返回值必须是长度为 4 的列表。"""
        result = rsrp_to_color(-90.0)
        assert isinstance(result, list) and len(result) == 4

    def test_alpha_is_200(self):
        """Alpha 通道固定为 200。"""
        assert rsrp_to_color(-80.0)[3] == 200
        assert rsrp_to_color(-100.0)[3] == 200
        assert rsrp_to_color(-120.0)[3] == 200


# ════════════════════════════════════════════════════════════
# 3. normalize_elevation 单元测试
# ════════════════════════════════════════════════════════════

class TestNormalizeElevation:
    """测试下载速率到柱高的归一化逻辑。"""

    def test_min_maps_to_zero(self):
        """最小值应归一化为 0。"""
        s = pd.Series([100.0, 500.0, 1000.0])
        result = normalize_elevation(s)
        assert result.min() == pytest.approx(0.0)

    def test_max_maps_to_scale(self):
        """最大值应归一化为 scale（默认 800）。"""
        s = pd.Series([100.0, 500.0, 1000.0])
        result = normalize_elevation(s)
        assert result.max() == pytest.approx(800.0)

    def test_custom_scale(self):
        """自定义 scale=400 时，最大值应等于 400。"""
        s = pd.Series([0.0, 50.0, 100.0])
        result = normalize_elevation(s, scale=400.0)
        assert result.max() == pytest.approx(400.0)

    def test_constant_series_no_error(self):
        """所有值相同时不应抛出除零错误，返回 scale/2。"""
        s = pd.Series([300.0, 300.0, 300.0])
        result = normalize_elevation(s)
        assert all(result == 400.0)         # scale/2 = 800/2

    def test_output_length_matches_input(self):
        """输出长度必须与输入一致。"""
        s = pd.Series([10.0, 20.0, 30.0, 40.0])
        assert len(normalize_elevation(s)) == len(s)


# ════════════════════════════════════════════════════════════
# 4. apply_filters 单元测试
# ════════════════════════════════════════════════════════════

class TestApplyFilters:
    """测试侧边栏联动筛选的过滤逻辑。"""

    def test_filter_by_single_band(self, enriched_df):
        """筛选单一频段，结果只含该频段数据。"""
        result = apply_filters(enriched_df, ["n28"], ["Smartphone", "CPE", "IoT"], (-130, 0))
        assert set(result["Band"].unique()) == {"n28"}

    def test_filter_by_terminal_type(self, enriched_df):
        """筛选单一终端类型，结果只含该终端数据。"""
        result = apply_filters(enriched_df, ["n28", "n41", "n78"], ["IoT"], (-130, 0))
        assert set(result["TerminalType"].unique()) == {"IoT"}

    def test_filter_by_rsrp_range(self, enriched_df):
        """RSRP 滑动条应排除范围外的点。"""
        result = apply_filters(enriched_df, ["n28", "n41", "n78"], ["Smartphone", "CPE", "IoT"], (-100, -80))
        assert result["RSRP_dBm"].between(-100, -80).all()

    def test_all_filters_combined(self, enriched_df):
        """三类筛选条件同时生效时，结果应满足所有条件。"""
        result = apply_filters(enriched_df, ["n28"], ["Smartphone"], (-95, -80))
        assert all(result["Band"] == "n28")
        assert all(result["TerminalType"] == "Smartphone")
        assert result["RSRP_dBm"].between(-95, -80).all()

    def test_no_match_returns_empty(self, enriched_df):
        """没有匹配项时应返回空 DataFrame，不抛异常。"""
        result = apply_filters(enriched_df, ["n78"], ["Smartphone"], (-70, -60))
        assert result.empty

    def test_does_not_modify_original(self, enriched_df):
        """筛选不应修改原始 DataFrame。"""
        original_len = len(enriched_df)
        apply_filters(enriched_df, ["n28"], ["Smartphone"], (-130, 0))
        assert len(enriched_df) == original_len


# ════════════════════════════════════════════════════════════
# 5. build_bar_chart 单元测试
# ════════════════════════════════════════════════════════════

class TestBuildBarChart:
    """测试柱状图构建函数的输出结构。"""

    def test_returns_figure(self, enriched_df):
        """应返回 Plotly Figure 对象。"""
        fig = build_bar_chart(enriched_df)
        assert isinstance(fig, go.Figure)

    def test_bar_trace_exists(self, enriched_df):
        """Figure 中应包含至少一个 Bar trace。"""
        fig = build_bar_chart(enriched_df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1

    def test_x_axis_contains_bands(self, enriched_df):
        """Bar 的 x 轴值应为频段名称。"""
        fig = build_bar_chart(enriched_df)
        x_values = set(fig.data[0].x)
        assert x_values.issubset({"n28", "n41", "n78"})

    def test_single_band_data(self, enriched_df):
        """只含一个频段时，图表也应正常渲染。"""
        df_single = enriched_df[enriched_df["Band"] == "n28"]
        fig = build_bar_chart(df_single)
        assert len(fig.data[0].x) == 1


# ════════════════════════════════════════════════════════════
# 6. build_pie_chart 单元测试
# ════════════════════════════════════════════════════════════

class TestBuildPieChart:
    """测试环形饼图构建函数的输出结构。"""

    def test_returns_figure(self, enriched_df):
        """应返回 Plotly Figure 对象。"""
        fig = build_pie_chart(enriched_df)
        assert isinstance(fig, go.Figure)

    def test_pie_trace_exists(self, enriched_df):
        """Figure 中应包含至少一个 Pie trace。"""
        fig = build_pie_chart(enriched_df)
        pie_traces = [t for t in fig.data if isinstance(t, go.Pie)]
        assert len(pie_traces) >= 1

    def test_labels_are_terminal_types(self, enriched_df):
        """Pie 的 labels 应为终端类型名称。"""
        fig = build_pie_chart(enriched_df)
        labels = set(fig.data[0].labels)
        assert labels.issubset({"Smartphone", "CPE", "IoT"})

    def test_values_sum_equals_total_rows(self, enriched_df):
        """各扇区 values 之和应等于数据行数。"""
        fig = build_pie_chart(enriched_df)
        assert sum(fig.data[0].values) == len(enriched_df)

    def test_hole_is_set(self, enriched_df):
        """环形图 hole 属性应大于 0（即为环形而非实心饼）。"""
        fig = build_pie_chart(enriched_df)
        assert fig.data[0].hole > 0
