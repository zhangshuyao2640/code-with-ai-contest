# 📡 5G 信号质量监控看板

基于 Streamlit + pydeck 构建的本地 Web 数据可视化看板，将 5G 信号采样数据渲染为 **3D 柱状地图**，并提供侧边栏联动筛选与频段、终端分布统计图表。

---

## 📁 文件结构

```
your-folder/
├── dashboard.py          # 看板主程序
├── run.py                # 一键启动脚本
├── requirements.txt      # Python 依赖
└── signal_samples.csv    # 信号采样数据
```

---

## 🖥️ 环境要求

- **Python 3.8 或以上**（推荐 3.11）
- macOS / Windows / Linux 均支持
- 无需任何地图 API Key（使用 CARTO Dark Matter 免费暗色底图）

---

## 🚀 快速开始

### 第一步：确认 Python 版本

```bash
python3 --version
```

如果版本低于 3.8，从以下地址下载安装 Python 3.11：

- **官网**：https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg
- **华为镜像（国内推荐）**：https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-macos11.pkg

双击 `.pkg` 文件，一路点继续完成安装。

---

### 第二步：将所有文件放入同一目录

确保以下四个文件在**同一个文件夹**下：

```
dashboard.py  /  run.py  /  requirements.txt  /  signal_samples.csv
```

---

### 第三步：一键启动

```bash
python3 run.py
```

脚本会自动完成：
1. 检测 Python 版本
2. 创建虚拟环境 `.venv`（不污染全局环境）
3. 安装所有依赖（首次运行较慢，约 1~3 分钟）
4. 启动看板，浏览器自动打开 `http://localhost:8501`

> 按 `Ctrl+C` 停止服务。

---

## 🔄 重置环境

如果依赖安装出错或需要重装，删除虚拟环境后重新运行：

```bash
rm -rf .venv
python3 run.py
```

---

## 🗺️ 看板功能介绍

### 🎛️ 侧边栏联动筛选

看板左侧提供三类筛选控件，所有图表和地图**实时联动**更新：

| 控件 | 说明 |
|------|------|
| 📶 频段多选 | 可多选 n28 / n41 / n78，取消勾选即从地图和图表中移除该频段 |
| 📱 终端类型多选 | 可多选 Smartphone / CPE / IoT |
| 📡 RSRP 范围滑动条 | 拖动两端滑块筛选信号强度范围（dBm） |

> 若所有频段或终端类型均被取消选择，看板会给出提示并停止渲染，避免空数据报错。

---

### 顶部 KPI 卡片

KPI 数值**基于当前筛选结果**实时计算：

| 指标 | 说明 |
|------|------|
| 筛选点数 | 当前筛选条件下的记录数 |
| 信号优秀点 | RSRP > -90 dBm 的点数 |
| 信号较差点 | RSRP < -110 dBm 的点数 |
| 平均下载速率 Mbps | 筛选后所有采样点的 Download_Mbps 均值 |

---

### 3D 地理分布地图（pydeck ColumnLayer）

采用 **pydeck ColumnLayer** 渲染 3D 柱状地图，底图使用 CARTO Dark Matter 暗色风格：

- **柱体高度**：由下载速率（Download_Mbps）归一化决定，速率越高柱越高
- **柱体颜色**：由 RSRP 信号强度决定：

  | 颜色 | 信号强度 | 含义 |
  |------|----------|------|
  | 🟢 绿色 | RSRP > -90 dBm | 信号优秀 |
  | 🟡 黄色 | -110 ~ -90 dBm | 信号中等 |
  | 🔴 红色 | RSRP < -110 dBm | 信号较差 |

- **鼠标悬停 Tooltip**：显示基站编号、频段、RSRP（dBm）、SINR（dB）、终端类型、下载速率、信号等级
- **初始视角**：俯仰角 50°，轻微旋转 -10°，呈现明显 3D 透视效果

> 切换筛选条件后，地图柱高会重新归一化，保证相对分布正确。

---

### 底部图表（联动筛选）

| 图表 | 说明 |
|------|------|
| 柱状图 | 各频段（n28 / n41 / n78）的唯一基站数量对比，随筛选实时更新 |
| 环形饼图 | Smartphone / CPE / IoT 三类终端的占比分布，随筛选实时更新 |

---

## ❓ 常见问题

**Q: `command not found: streamlit`**
> 已通过 `python -m streamlit` 方式调用，无需手动激活虚拟环境，直接运行 `python3 run.py` 即可。

**Q: `No matching distribution found for streamlit`**
> Python 版本过低，请升级到 3.11，参考第一步安装说明。

**Q: `ImportError: Unable to import required dependency numpy`**
> 删除旧虚拟环境后重新安装：
> ```bash
> rm -rf .venv && python3 run.py
> ```

**Q: `brew install` 报 GitHub 网络错误**
> 不需要 Homebrew，直接用上方华为镜像下载 Python 安装包即可。

**Q: 地图显示空白**
> 检查网络是否能访问 CARTO 底图服务（`basemaps.cartocdn.com`），3D 地图底图需要联网加载。

**Q: 切换筛选后地图柱高分布变化**
> 属于正常现象。筛选后的子集会重新做 min-max 归一化，以保证柱高相对分布始终清晰可读。

---

## 📦 依赖清单

| 包 | 用途 |
|----|------|
| `streamlit` | Web 看板框架 |
| `pandas` | 数据读取与处理 |
| `numpy` | 数值计算基础依赖 |
| `pydeck` | 基于 WebGL 的 3D 柱状地图渲染 |
| `plotly` | 柱状图与饼图渲染 |
