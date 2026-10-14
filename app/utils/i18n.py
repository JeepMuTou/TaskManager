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
    "time_range_enable":    {"zh": "仅在指定时间范围内运行", "en": "Run only during time range"},
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
    "settings_version":     {"zh": "版本信息", "en": "Version Info"},
    "settings_save":        {"zh": "保存", "en": "Save"},
    "settings_cancel":      {"zh": "取消", "en": "Cancel"},
    "settings_saved_title": {"zh": "已保存", "en": "Saved"},
    "settings_auto_fix":    {"zh": "检测/修复所有环境", "en": "Check/Fix All Envs"},
    "env_ok":               {"zh": "所有任务环境检测正常，均已具备运行条件！", "en": "All task environments are ready!"},
    "env_missing":          {"zh": "检测到以下任务环境未就绪：\n{tasks}\n\n是否立即启动安装程序？", "en": "The following task environments are not ready:\n{tasks}\n\nInstall now?"},
    "env_fixing":           {"zh": "已在独立控制台窗口中启动环境安装，请在窗口中查看安装进度。", "en": "Installation started in a new console window. Please check progress there."},
    "btn_task_env":         {"zh": "环境检测/安装", "en": "Env Check/Install"},
    "task_env_ok_title":    {"zh": "环境就绪", "en": "Environment Ready"},
    "task_env_ok_msg":      {"zh": "当前任务环境检测正常，已具备运行条件！", "en": "Environment for this task is ready!"},
    "task_env_fail_title":  {"zh": "环境未就绪", "en": "Environment Not Ready"},
    "task_env_fail_msg":    {"zh": "该任务环境检测未通过：\n\n{detail}\n\n是否立即启动安装程序？", "en": "Task environment check failed:\n\n{detail}\n\nInstall now?"},
    "task_env_installing_title": {"zh": "环境安装已启动", "en": "Installation Started"},
    "task_env_installing_msg": {"zh": "已在独立控制台窗口中启动环境安装，请在窗口中查看安装进度。", "en": "Installation started in a new console window. Please check progress there."},
    "settings_saved_msg":   {"zh": "设置已保存，部分设置将在下次启动时生效。",
                             "en": "Settings saved. Some changes take effect on next launch."},
    "settings_auto_update": {"zh": "开启自动更新检查", "en": "Enable Auto Update Check"},
    "settings_check_update": {"zh": "检查更新", "en": "Check Update"},
    "update_checking": {"zh": "检查中...", "en": "Checking..."},
    "update_available_title": {"zh": "发现新版本", "en": "Update Available"},
    "update_available_msg": {"zh": "发现新版本的任务管理器，是否立即更新？", "en": "A new version is available. Update now?"},
    "update_no_title": {"zh": "已经是最新版本", "en": "Up to date"},
    "update_no_msg": {"zh": "当前已是最新版本，无需更新。", "en": "You are currently using the latest version."},
    "update_error_title": {"zh": "检查更新失败", "en": "Check Update Failed"},
    "update_error_msg": {"zh": "无法检查更新，请检查网络或配置。", "en": "Failed to check for updates. Please check your network or configuration."},
}


def tr(key: str, lang: str = "zh") -> str:
    """翻译函数"""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("zh", key))
