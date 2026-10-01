import os
import subprocess
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

class TaskManager:
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
        self.running_processes = {}

    def scan_tasks(self) -> List[Dict[str, Any]]:
        """扫描 tasks_dir 下的子目录，寻找 schema.json 配置文件"""
        tasks = []
        if not self.tasks_dir.exists():
            return tasks

        for item in self.tasks_dir.iterdir():
            if item.is_dir():
                schema_file = item / "UI" / "schema.json"
                if schema_file.exists():
                    schema = self._get_task_schema(schema_file)
                    if schema:
                        # 补充一个内部的 task_id 字段 (使用文件夹名称)
                        schema['task_id'] = item.name
                        tasks.append(schema)
        return tasks

    def _get_task_schema(self, schema_file: Path) -> Dict[str, Any]:
        """读取任务的 schema.json"""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取 {schema_file} schema 失败: {e}")
            return {}

    def execute_task(self, task_id: str, params: dict):
        """执行指定任务，这通常由 Scheduler 调用"""
        task_dir = self.tasks_dir / task_id
        script_path = task_dir / "run.py"
        if not script_path.exists():
            print(f"Task script not found: {script_path}")
            return

        try:
            python_exe = sys.executable
            # 异步执行，不阻塞主程序
            # Windows 下可以使用 CREATE_NO_WINDOW 避免弹出黑框
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                [python_exe, "run.py"],
                cwd=str(task_dir),
                creationflags=creationflags
            )
            self.running_processes[task_id] = proc
            print(f"已启动任务: {task_id}")
        except Exception as e:
            print(f"启动任务 {task_id} 失败: {e}")

    def is_task_running(self, task_id: str) -> bool:
        """检查特定任务是否仍在运行"""
        proc = self.running_processes.get(task_id)
        if proc is None:
            return False
            
        if proc.poll() is None:
            # 进程仍在运行
            return True
        else:
            # 进程已结束，清理记录
            del self.running_processes[task_id]
            return False

    def get_dynamic_options(self, task_id: str, param_name: str) -> List[str]:
        """向特定脚本请求动态选项列表"""
        task_dir = self.tasks_dir / task_id
        script_path = task_dir / "UI" / "api.py"
        if not script_path.exists():
            return []
            
        try:
            python_exe = sys.executable
            # 允许适当长一点的时间 (如 10 秒) 以防 Outlook 卡顿
            result = subprocess.run(
                [python_exe, "UI/api.py", "--get-options", param_name],
                cwd=str(task_dir),
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            output = result.stdout.strip()
            # 尝试解析最后有效 JSON
            lines = output.split('\n')
            for line in reversed(lines):
                if line.startswith('[') and line.endswith(']'):
                    return json.loads(line)
            return json.loads(output)
        except subprocess.TimeoutExpired:
            print(f"获取选项超时: {param_name}")
            return []
        except Exception as e:
            print(f"获取动态选项失败 {task_id}.{param_name}: {e}")
            return []
