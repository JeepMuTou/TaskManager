from apscheduler.schedulers.background import BackgroundScheduler
from typing import Callable

class SchedulerManager:
    def __init__(self, task_executor: Callable[[str, dict], None]):
        self.scheduler = BackgroundScheduler()
        self.task_executor = task_executor
        self.scheduler.start()

    def schedule_task(self, task_id: str, config: dict):
        """安排一个任务执行"""
        self.remove_task(task_id)
        
        if not config.get("enabled", False):
            return
            
        params = config.get("params", {})
        schedule_type = config.get("schedule_type", "weekly") # 默认设为 weekly
        
        try:
            if schedule_type == "interval":
                interval_seconds = config.get("interval_seconds", 60)
                job_id = f"job_{task_id}_0"
                self.scheduler.add_job(
                    self.task_executor,
                    'interval',
                    seconds=interval_seconds,
                    args=[task_id, params],
                    id=job_id,
                    replace_existing=True
                )
                print(f"任务 {task_id} (间隔) 已加入调度，周期: {interval_seconds} 秒")
                
            elif schedule_type == "weekly":
                weekly_schedule = config.get("weekly_schedule", {})
                days = weekly_schedule.get("days", [])
                
                # 兼容旧版的 time (单个时间) 和 新版的 times (多个时间)
                times = weekly_schedule.get("times", [])
                if not times and "time" in weekly_schedule:
                    times = [weekly_schedule["time"]]
                if not times:
                    times = ["00:00"]
                    
                if not days:
                    print(f"任务 {task_id} (每周) 缺少日期配置，无法调度。")
                    return
                    
                day_of_week = ",".join(days)
                
                for idx, time_str in enumerate(times):
                    hour, minute = map(int, time_str.split(':'))
                    job_id = f"job_{task_id}_{idx}"
                    
                    self.scheduler.add_job(
                        self.task_executor,
                        'cron',
                        day_of_week=day_of_week,
                        hour=hour,
                        minute=minute,
                        args=[task_id, params],
                        id=job_id,
                        replace_existing=True
                    )
                    print(f"任务 {task_id} (每周) 已加入调度 [{idx}]，星期: {day_of_week}, 时间: {time_str}")
        except Exception as e:
            print(f"添加调度任务 {task_id} 时出错: {e}")

    def remove_task(self, task_id: str):
        """移除该任务的所有相关调度 (基于前缀)"""
        prefix = f"job_{task_id}_"
        jobs = self.scheduler.get_jobs()
        removed_count = 0
        for job in jobs:
            # 兼容以前的 job_taskid 命名和新的 job_taskid_idx 命名
            if job.id == f"job_{task_id}" or job.id.startswith(prefix):
                self.scheduler.remove_job(job.id)
                removed_count += 1
                
        if removed_count > 0:
            print(f"任务 {task_id} 已从调度中移除 ({removed_count} 个时间点)")

    def shutdown(self):
        self.scheduler.shutdown()
