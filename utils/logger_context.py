import datetime
from typing import Optional, TextIO

class LoggerContext:
    def __init__(self, action: str = "Executing block", log_file="task_manager.log"):
        self.action = action
        self.log_file = log_file
        self._log_handle: Optional[TextIO] = None

    def __enter__(self):
        self._log_handle = open(self.log_file, "a")
        self._write_log(f"🔄 Starting: {self.action}")
        print(f"🔄 [{self._timestamp()}] Starting: {self.action}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self._write_log(f"💥 Error during: {self.action} — {exc_value}")
            print(f"💥 [{self._timestamp()}] Error during: {self.action} — {exc_value}")
        else:
            self._write_log(f"✅ Finished: {self.action}")
            print(f"✅ [{self._timestamp()}] Finished: {self.action}")
        self._write_log("🟢 Session ended\n")
        if self._log_handle:
            self._log_handle.close()
        return False  # Let exceptions propagate

    def _timestamp(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write_log(self, message: str):
        if self._log_handle is None:
            raise RuntimeError("Log handle not initialized.")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log_handle.write(f"[{timestamp}] {message}\n")
        
    def log(self, message: str):
        if self._log_handle:
            self._write_log(f"📝 {message}")
            print(f"📝 [{self._timestamp()}] {message}")