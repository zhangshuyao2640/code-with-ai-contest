#!/usr/bin/env python3
# ── 5G 信号质量看板 · 一键启动脚本 ──────────────────────────

import sys
import os
import subprocess
import shutil
from pathlib import Path

VENV_DIR = Path(".venv")
SCRIPT_DIR = Path(__file__).parent
REQUIREMENTS = SCRIPT_DIR / "requirements.txt"
DASHBOARD = SCRIPT_DIR / "dashboard.py"
CSV_FILE = SCRIPT_DIR / "signal_samples.csv"

# ── 工具函数 ───────────────────────────────────────────────
def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)

def find_python():
    """优先选高版本 Python，最低要求 3.8"""
    candidates = ["python3.11", "python3.10", "python3.9", "python3.8", "python3", "python"]
    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        result = subprocess.run(
            [path, "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
            capture_output=True, text=True
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

# 1. 检查 Python 版本
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

# 4. 确定虚拟环境内的 Python / pip 路径
if sys.platform == "win32":
    venv_python = VENV_DIR / "Scripts" / "python.exe"
    venv_pip    = VENV_DIR / "Scripts" / "pip.exe"
else:
    venv_python = VENV_DIR / "bin" / "python"
    venv_pip    = VENV_DIR / "bin" / "pip"

# 5. 升级 pip
print("📦 安装依赖（首次较慢，请耐心等待）...")
run([str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])

# 6. 安装依赖
run([str(venv_python), "-m", "pip", "install", "--quiet", "-r", str(REQUIREMENTS)])

# 7. 启动 Streamlit
print()
print("✅ 依赖安装完成，正在启动看板...")
print("🌐 浏览器将自动打开 http://localhost:8501")
print("   按 Ctrl+C 可停止服务")
print("─────────────────────────────────")
print()

os.chdir(SCRIPT_DIR)
os.execv(str(venv_python), [str(venv_python), "-m", "streamlit", "run", str(DASHBOARD)])
