import argparse
import json
import sys
import time
import os
from datetime import datetime

def get_dynamic_options():
    # 模拟耗时操作，例如查询数据库获取可选项
    # time.sleep(0.5)
    return ["Server_Alpha", "Server_Beta", "Server_Gamma"]

def get_config_schema():
    """返回该任务的配置项结构，供主程序动态生成 UI"""
    return {
        "task_name": "数据同步演示任务",
        "description": "定时将本地数据同步到远端服务器 (示例)",
        "parameters": [
            {
                "name": "target_server", 
                "type": "choice", 
                "options": get_dynamic_options(), 
                "label": "目标服务器"
            },
            {
                "name": "sync_path",
                "type": "string",
                "default": "/var/data",
                "label": "远端同步路径"
            },
            {
                "name": "timeout", 
                "type": "int", 
                "default": 30, 
                "label": "超时时间(秒)"
            },
            {
                "name": "enable_log", 
                "type": "bool", 
                "default": True, 
                "label": "记录执行日志"
            }
        ]
    }

def run_task(params):
    """实际执行任务的逻辑"""
    server = params.get('target_server', 'Unknown')
    path = params.get('sync_path', '/')
    timeout = params.get('timeout', 30)
    enable_log = params.get('enable_log', False)
    
    msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在向 {server}:{path} 同步数据，超时为 {timeout} 秒..."
    print(msg)
    
    # 将日志持久化到当前任务的 data/ 目录下
    if enable_log:
        os.makedirs("data", exist_ok=True)
        with open("data/run_log.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
            
    # 模拟任务执行
    time.sleep(1)
    print("同步完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get-schema", action="store_true", help="获取配置项结构")
    parser.add_argument("--run", type=str, help="执行任务，传入 JSON 格式的参数")
    args = parser.parse_args()

    if args.get_schema:
        print(json.dumps(get_config_schema()))
        sys.exit(0)
    
    if args.run:
        try:
            params = json.loads(args.run)
            run_task(params)
        except Exception as e:
            print(f"任务执行失败: {e}")
            sys.exit(1)
        sys.exit(0)
