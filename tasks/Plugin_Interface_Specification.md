# TaskManager 插件接口规范 (Plugin Interface Specification)

TaskManager 采用了高度解耦的**去中心化配置**架构。主程序（Manager）只负责任务的发现、定时调度以及进程的拉起，而每个任务（Task）完全掌控自己的业务逻辑与配置界面。

为了让您的任务能够被主程序正确识别并调度，请在开发新任务时严格遵守以下规范。

## 1. 目录结构契约

任何存放在 `tasks/` 目录下的子文件夹，都会被主程序视为一个独立的任务插件。
一个标准的任务文件夹（如 `tasks/my_custom_task/`）建议包含以下核心文件：

```text
my_custom_task/
├── metadata.json       # 必选：插件元数据，用于主界面展示
├── config_ui.py        # 必选：独立的参数配置界面入口 (亦可为 config_ui.bat)
├── run.bat             # 必选：任务的启动入口（可调用 python/node/exe 等任何脚本或程序）
├── check_env.bat       # 推荐：任务环境检测脚本（退出码 0 表示就绪，非 0 表示缺失）
├── install_env.bat     # 推荐：任务环境安装脚本（独立控制台运行，退出码 0 表示成功）
├── run.py              # 业务执行脚本（由 run.bat 负责调用）
└── config.json         # 自动生成：持久化配置文件（业务参数+调度参数）
```

## 2. 核心文件规范详解

### 2.1 元数据文件 (`metadata.json`)
这是任务的“身份证”，主程序通过读取它来在左侧列表中展示任务信息。
**格式要求**：
```json
{
    "name": "我的自定义任务",
    "description": "这是对该任务的一段简短描述，说明它的主要功能。"
}
```

### 2.2 配置界面程序 (`config_ui.py`)
当用户在主界面点击“打开任务配置界面”时，主程序会作为一个独立的子进程执行此文件（也支持 `config_ui.bat`）。
- **职责**：弹出一个属于该任务特有的 UI 窗口（您可以使用 PySide6、Tkinter 等任何 GUI 库）。
- **数据流向**：该界面应允许用户填写业务所需的参数（如账号、密码、阈值等），并在用户点击“保存”时，将这些参数写入到同目录下的 `config.json` 文件的 `params` 节点中。

### 2.3 任务执行入口 (`run.bat`)
当到达定时调度的触发时间，或用户在主界面点击“立即运行”时，主程序会在后台无窗口执行 `run.bat`。
- **启动入口 (`run.bat`)**：主程序将通过 `run.bat` 拉起任务。主程序会自动注入环境变量 `%PYTHON_EXE%`。若 `run.bat` 缺省但存在 `run.py`，主程序会自动生成标准模板。由于执行的是 bat 文件，您可以自由调用 Python、Node.js、Go、C++ 编译的可执行程序等任何运行环境。
- **工作目录 (CWD)**：主程序在拉起时会**强制将当前工作目录设置为任务自身的根目录**。因此，您在代码中读写文件（如保存数据到 `data/` 或是写日志到 `Log/`）时，**直接使用相对路径即可**，无需拼接绝对路径。
- **日志建议**：由于是在后台运行，建议将重要的报错捕获并写入到本地日志文件中，以免报错信息丢失。

### 2.4 环境检测与安装脚本 (`check_env.bat` & `install_env.bat`)
为了实现不同任务技术栈的彻底解耦，每个任务可以定义自己所需的环境校验与自动安装流程：
- **环境检测 (`check_env.bat`)**：
  - 由主程序在后台无窗口静默执行。
  - **退出码契约**：如果检测到依赖完备，返回 `exit /b 0`；如果缺少 Python、Node 或第三方依赖库，输出具体错误原因到控制台并返回 `exit /b 1`。
- **环境安装 (`install_env.bat`)**：
  - 当环境未就绪且用户确认安装时，主程序会在**独立的控制台窗口**中调起该脚本，方便用户实时查看安装日志与下载进度（如 `pip install -r requirements.txt` 或 `npm install`）。
  - **退出码契约**：安装成功返回 `exit /b 0`，失败返回非 0。

## 3. 配置文件 (`config.json`) 的共享机制

`config.json` 是主程序与任务脚本之间传递数据的唯一桥梁。它包含两部分数据：
- `params` 节点：由您的 `config_ui.py` 负责维护，存放业务特有参数。
- 根级其他节点（如 `enabled`, `schedule_type`, `interval_seconds` 等）：由**主程序**负责维护，存放全局定时调度策略。

**🚨 关键注意**：在开发 `config_ui.py` 并向 `config.json` 写入数据时，为了避免意外抹除主程序的调度配置，请务必**采用增量/合并写入**的方式（即先读取旧的 json，仅覆盖 `params` 节点，再整体写回）。

**标准写入示例 (Python)**：
```python
import json
import os

config_file = "config.json"
config = {}

# 1. 尝试读取现有的全局配置（保护主程序的调度参数）
if os.path.exists(config_file):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception:
        pass

# 2. 仅更新 params 节点
config["params"] = {
    "target_email": "admin@example.com",
    "max_count": 100
}

# 3. 整体写回
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)
```

## 4. 运行环境说明
得益于架构的解耦设计，未来的主程序无论是否被编译为独立的 `.exe` 文件，在拉起 `run.py` 和 `config_ui.py` 时，都会利用智能机制调用当前系统环境变量 (PATH) 中的 `python` 解释器。因此，插件开发者可以放心使用标准 Python 库，只需确保部署的主机上正确安装了所需的运行环境即可。
