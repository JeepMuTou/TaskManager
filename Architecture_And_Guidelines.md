# Task Manager 项目架构与开发规范文档

本文档旨在梳理 `TaskManager` 项目的整体架构、核心模块、组件间接口以及后续开发和维护所需遵循的规范。

## 1. 项目整体架构

本项目采用 **核心调度框架 + 可插拔任务模块 (Core + Plugins)** 的架构模式。
主程序（基于 PySide6/PyQt 构建的 GUI）负责界面展示、任务扫描、动态配置渲染以及定时调度；具体的业务逻辑（如读取 Outlook 邮件）被封装在独立的作用域内，作为“任务插件”供主程序调用。

### 1.1 目录结构

```text
Source/
├── main.py                     # 应用程序入口
├── app/                        # 核心框架层
│   ├── gui/                    # 界面层
│   │   ├── main_window.py      # 主窗口界面，统筹左侧任务列表、右侧配置项与调度面板
│   │   └── dynamic_form.py     # 核心 UI 引擎，根据 schema.json 动态渲染配置表单
│   ├── core/                   # 逻辑核心层
│   │   ├── task_manager.py     # 任务管理器，负责扫描 tasks 目录、管理进程及执行脚本
│   │   └── scheduler.py        # 定时任务调度器，支持间隔循环 (interval) 与按周定时 (weekly)
│   └── utils/
│       └── config_store.py     # 配置存储工具，统一管理任务级别的 config.json 的读写
└── tasks/                      # 可插拔任务模块层
    └── outlook_reader/         # 具体任务实例（例如：Outlook 邮件读取器）
        ├── run.py              # 任务执行入口脚本（无头运行）
        ├── config.json         # 任务实例的持久化配置文件（由主程序自动生成及维护）
        ├── data/               # 任务产生的数据目录（例如导出的 Excel）
        ├── Log/                # 任务运行的日志输出目录
        └── UI/
            └── schema.json     # 任务配置表单的蓝图定义文件
```

---

## 2. 模块交互接口规范

### 2.1 主程序与任务的解耦机制
任务（Task）与主框架（App）之间通过**配置解耦**与**进程解耦**来进行通信。主框架不直接调用任务内部的 Python 函数，而是通过 `subprocess` 或线程的方式执行任务目录下的 `run.py` 脚本。

1. **信息输入（App -> Task）**: 主程序读取 `UI/schema.json` 渲染界面，用户填写的参数会保存在任务根目录的 `config.json` 中。
2. **任务执行（Task 读取配置）**: `run.py` 启动时，主动读取同级目录下的 `config.json` 获取运行所需的 `params` 参数。

### 2.2 动态表单 (Dynamic Form) 与 Schema 定义规范
每个新建的 Task 都必须在 `UI/schema.json` 中声明自己所需的配置项。`app.gui.dynamic_form.py` 会负责解析该文件并动态生成输入框。

**Schema 格式示例与支持的类型：**
```json
{
    "task_name": "任务展示名称",
    "description": "任务的详细描述",
    "parameters": [
        {
            "name": "target_account",         // 在 config.json 中保存的 key
            "type": "dynamic_editable_list",  // 控件类型
            "label": "监控邮箱账户"            // 左侧显示的标签文字
        },
        {
            "name": "max_emails",
            "type": "int",                    // 支持 int, float, string, bool, password, choice 等
            "default": 500,                   // 默认值
            "label": "单次最多读取封数"
        }
    ]
}
```

**已知扩展控件规范 (重点)：**
- `dynamic_editable_list`: 用于渲染**可增删的列表项**（附带 CheckBox 选中机制）。它会生成一个输入框供用户添加新元素，下方是一个复选列表。**返回值**：用户选中项的 `List[str]`。
- `dynamic_info`: 用于渲染**只读统计信息**。它不参与 `config.json` 的保存操作。

---

## 3. 具体任务 (Task) 的开发规范

如果您需要在此框架下开发一个新的任务模块（例如 `tasks/new_crawler`），请务必遵循以下步骤和规范：

1. **基本结构**：
   在 `tasks/` 下新建一个文件夹。必须包含 `run.py`（执行逻辑）和 `UI/schema.json`（表单定义）。
2. **配置读取规范**：
   在 `run.py` 的起始部分，必须从同级目录读取 `config.json`，并提取其中的 `params` 节点。示例：
   ```python
   import json, os
   if os.path.exists("config.json"):
       with open("config.json", "r", encoding="utf-8") as f:
           config = json.load(f)
           params = config.get("params", {})
   ```
3. **工作目录 (CWD)**：
   任务被主程序调用时，其运行的当前工作目录 (Current Working Directory) 必定是**该任务的根目录**（例如 `Source/tasks/new_crawler`）。因此代码中对于 `data/`、`Log/` 文件夹的创建和读写，直接使用相对路径即可。
4. **日志输出规范**：
   - 任务必须在自己内部捕获异常（使用 `try...except Exception:` 和 `traceback`）。
   - 除了终端的 `print`，所有关键节点和异常报错建议写入到本目录的 `Log/` 文件夹内，以免 UI 在后台调度时丢失关键报错信息。

---

## 4. UI 开发与定制注意事项

1. **QSS 样式隔离**：
   在修改或定制 PyQt/PySide 的控件样式时，如果需要用到透明背景等高级特性（如 `background: transparent;`），**务必使用 ID 选择器限制样式的作用域**（例如 `QWidget#MyContainer`）。全局设定透明或异常背景会导致原生子控件（如 `QCheckBox`）的渲染引擎崩溃（表现为复选框变白、无法显示选中对钩）。
2. **配置保存机制**：
   主界面的“保存配置”按钮（`on_save_config`）触发时，会将动态表单中获取到的值全量覆写到 `config.json` 里的 `params` 节点下。因此，当表单加入非保存型控件（如 `dynamic_info`）时，务必在 `dynamic_form.py` 的 `get_values()` 方法中明确 `pass` 跳过它。

---

## 5. 已存在任务 (Outlook Reader) 特别说明

- **核心功能**：读取指定邮箱的全文件夹邮件记录，支持历史增量合并去重，并内置“回复时序状态机”。
- **状态机机制**：
  为追踪业务邮件跟进情况，程序并非流水线式追加数据，而是将新旧邮件合并后按时间排序重算。
  当发送方在 `exclude_emails` （员工身份列表）内时，会自动向下匹配最早一封尚未回复的客户邮件（标题相似度 > 80% 且包含客户收件人）。匹配成功则覆写 Excel 中客户邮件的 `回复时间` 单元格。
- **配置注意事项**：
  若在 UI 中更改了 `排除邮箱列表` (员工身份识别后缀) 或 `目标账户`，**必须点击保存**后，`run.py` 才会在下一次执行时接收到最新的识别名单并正确执行。
