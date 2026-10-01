import json
import os
from pathlib import Path

class ConfigStore:
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)

    def _get_task_config_path(self, task_id: str) -> Path:
        return self.tasks_dir / task_id / "config.json"

    def get_task_config(self, task_id: str) -> dict:
        """获取特定任务的配置，如果不存在则返回空字典"""
        config_path = self._get_task_config_path(task_id)
        if not config_path.exists():
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config for {task_id}: {e}")
            return {}

    def save_task_config(self, task_id: str, config: dict):
        """保存特定任务的配置"""
        config_path = self._get_task_config_path(task_id)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save config for {task_id}: {e}")

    def get_all_tasks(self) -> dict:
        """返回所有存在 config.json 的任务配置"""
        all_configs = {}
        if not self.tasks_dir.exists():
            return all_configs
        
        for task_path in self.tasks_dir.iterdir():
            if task_path.is_dir():
                task_id = task_path.name
                config_path = task_path / "config.json"
                if config_path.exists():
                    all_configs[task_id] = self.get_task_config(task_id)
        return all_configs
