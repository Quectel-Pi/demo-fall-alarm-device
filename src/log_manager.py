# -*- coding: gbk -*-
"""日志管理类"""


class LogManager:
    _instance = None
    _logs = []
    _max_lines = 100 

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LogManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def append_log(cls, message: str, level: str = "INFO"):
        import time
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        cls._logs.append(log_line)

        if len(cls._logs) > cls._max_lines:
            cls._logs.pop(0)

    @classmethod
    def get_logs(cls) -> str:
        return "\n".join(cls._logs)

    @classmethod
    def clear_logs(cls):
        cls._logs.clear()
        
    @classmethod
    def get_log_lines(cls):
        return cls._logs.copy()

