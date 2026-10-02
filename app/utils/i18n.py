# 简易国际化翻译表
# 用法: from app.utils.i18n import tr
#       tr("key", lang)

_STRINGS = {
    # --- 主窗口 ---
    "window_title":         {"zh": "定时任务管理器", "en": "Task Manager"},
    "task_list_title":      {"zh": "可用任务列表", "en": "Task List"},
    "btn_app_config":       {"zh": "⚙️ 管理器配置", "en": "⚙️ Settings"},
    "select_task_hint":     {"zh": "请在左侧选择任务", "en": "Select a task on the left"},
    "desc_hint":            {"zh": "任务描述将在这里显示", "en": "Task description will appear here"},
    "no_desc":              {"zh": "无描述", "en": "No description"},
    "status_running":       {"zh": "🟢 运行中", "en": "🟢 Running"},
    
    # --- 调度区 ---
    "schedule_title":       {"zh": "定时调度策略", "en": "Schedule Policy"},
    "btn_task_config":      {"zh": "打开任务配置界面", "en": "Open Task Config"},
    "radio_weekly":         {"zh": "每周特定时间", "en": "Weekly"},
    "radio_interval":       {"zh": "固定时间间隔", "en": "Fixed Interval"},
    "interval_label":       {"zh": "调度周期 (秒):", "en": "Interval (sec):"},
    "exec_time_label":      {"zh": "执行时间:", "en": "Exec Time:"},
    "btn_add_time":         {"zh": " + 添加执行时间 ", "en": " + Add Time "},
    "timeout_prefix":       {"zh": "运行超过", "en": "Force stop after"},
    "timeout_suffix":       {"zh": "分钟后强制结束", "en": "mins"},
    "btn_save":             {"zh": "保存调度配置", "en": "Save Schedule"},
    "btn_run_now":          {"zh": "立即运行", "en": "Run Now"},
    "btn_running":          {"zh": "正在运行...", "en": "Running..."},
    "btn_stop_run":         {"zh": "结束运行", "en": "Stop Run"},
    "save_success_title":   {"zh": "成功", "en": "Success"},
    "save_success_msg":     {"zh": "调度设置已保存。如果该任务当前为启用状态，新的调度策略已生效。",
                             "en": "Schedule saved. If enabled, the new policy is now active."},
    
    # --- 星期 ---
    "day_mon": {"zh": "周一", "en": "Mon"},
    "day_tue": {"zh": "周二", "en": "Tue"},
    "day_wed": {"zh": "周三", "en": "Wed"},
    "day_thu": {"zh": "周四", "en": "Thu"},
    "day_fri": {"zh": "周五", "en": "Fri"},
    "day_sat": {"zh": "周六", "en": "Sat"},
    "day_sun": {"zh": "周日", "en": "Sun"},
    
    # --- 设置对话框 ---
    "settings_title":       {"zh": "管理器配置", "en": "Settings"},
    "settings_language":    {"zh": "界面语言", "en": "Language"},
    "settings_auto_start":  {"zh": "开机自动启动", "en": "Start on Boot"},
    "settings_minimize":    {"zh": "关闭时最小化到托盘", "en": "Minimize to Tray on Close"},
    "settings_parallel":    {"zh": "允许任务并行 (开启后任务可同时执行)", "en": "Allow Parallel Tasks"},
    "settings_save":        {"zh": "保存", "en": "Save"},
    "settings_cancel":      {"zh": "取消", "en": "Cancel"},
    "settings_saved_title": {"zh": "已保存", "en": "Saved"},
    "settings_auto_fix":    {"zh": "自动修复环境", "en": "Auto Fix Environment"},
    "env_ok":               {"zh": "环境正常\n当前已具备 Python 且满足所有依赖库。", "en": "Environment Normal.\nPython and all required libraries are installed."},
    "env_missing":          {"zh": "环境异常\n你的环境缺少 Python，或者缺少以下库：\n{libs}\n\n是否自动修复？", "en": "Environment missing Python or libraries:\n{libs}\n\nAuto fix?"},
    "env_fixing":           {"zh": "正在后台修复...\n系统正在自动下载并配置便携版 Python 及所需库，请约 10 分钟后重新检查。", "en": "Fixing in background...\nDownloading portable Python and libraries. Please check again in 10 minutes."},
    "settings_saved_msg":   {"zh": "设置已保存，部分设置将在下次启动时生效。",
                             "en": "Settings saved. Some changes take effect on next launch."},
}


def tr(key: str, lang: str = "zh") -> str:
    """翻译函数"""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("zh", key))
