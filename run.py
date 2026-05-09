"""
run.py
======
5G 信号质量看板 · 一键启动脚本
自动完成：Python 版本检测 → 创建虚拟环境 → 安装依赖 → 启动 Streamlit
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple

VENV_DIR    = Path(".venv")
SCRIPT_DIR  = Path(__file__).parent
REQUIREMENTS = SCRIPT_DIR / "requirements.txt"
DASHBOARD   = SCRIPT_DIR / "dashboard.py"
CSV_FILE    = SCRIPT_DIR / "signal_samples.csv"


def run(cmd: list, **kwargs):
    """执行子进程命令，失败时抛出异常。"""
    return subprocess.run(cmd, check=True, **kwargs)


def find_python() -> Tuple[Optional[str], Optional[str]]:
    """
    按优先级搜索可用的 Python 解释器（3.8+）。

    Returns:
        (python路径, 版本字符串) 或 (None, None)。
    """
    candidates = ["python3.11", "python3.10", "python3.9", "python3.8", "python3", "python"]
    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        result = subprocess.run(
            [path, "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            major, minor = map(int, result.stdout.strip().split())
            if (major, minor) >= (3, 8):
                return path, f"{major}.{minor}"
    return None, None


# ── 主流程 ─────────────────────────────────────────────────
print()
print("📡 5G 信号质量看板 - 启动中...")
print("─────────────────────────────────")

# 1. 检测 Python 版本
python_path, py_ver = find_python()
if not python_path:
    print("❌ 未找到 Python 3.8+，请先安装：")
    print("   https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-macos11.pkg")
    sys.exit(1)

print(f"🐍 使用 Python {py_ver}（{python_path}）")

# 2. 检查 CSV 文件
if not CSV_FILE.exists():
    print(f"❌ 未找到 signal_samples.csv，请将其与 run.py 放在同一目录下")
    sys.exit(1)

# 3. 创建虚拟环境
if not VENV_DIR.exists():
    print("🔧 创建虚拟环境 .venv ...")
    run([python_path, "-m", "venv", str(VENV_DIR)])

# 4. 虚拟环境内的 Python 路径
venv_python = (
    VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)

# 5. 安装依赖
print("📦 安装依赖（首次较慢，请耐心等待）...")
run([str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
run([str(venv_python), "-m", "pip", "install", "--quiet", "-r", str(REQUIREMENTS)])

print()
print("✅ 依赖安装完成！")
print()
print("  可选：运行单元测试")
print("  └─ python3 -m pytest test_dashboard.py -v")
print()
print("🌐 启动看板，浏览器将自动打开 http://localhost:8501")
print("   按 Ctrl+C 可停止服务")
print("─────────────────────────────────")
print()

# 6. 启动 Streamlit（用 execv 替换当前进程，Ctrl+C 行为一致）
os.chdir(SCRIPT_DIR)
os.execv(str(venv_python), [str(venv_python), "-m", "streamlit", "run", str(DASHBOARD)])