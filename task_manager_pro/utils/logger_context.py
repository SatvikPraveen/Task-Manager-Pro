"""
utils/logger_context.py

Defines a context manager for logging execution blocks with timestamps.
Handles start, success, and error logs automatically, and writes them to a log file.
Useful for tracking actions in long-running or critical sections of the CLI tool.
"""

import datetime
from typing import Optional, TextIO

class LoggerContext:
    def __init__(self, action: str = "Executing block", log_file="task_manager.log"):
        """
        Initializes the context logger.

        Args:
            action (str): Description of the action being logged.
            log_file (str): Path to the log file. Defaults to 'task_manager.log'.
        """
        self.action = action
        self.log_file = log_file
        self._log_handle: Optional[TextIO] = None

    def __enter__(self):
        """
        Enters the context block, opens the log file, and logs the start of the action.

        Returns:
            LoggerContext: Returns self for optional inline logging via .log().
        """
        self._log_handle = open(self.log_file, "a")
        self._write_log(f"🔄 Starting: {self.action}")
        print(f"🔄 [{self._timestamp()}] Starting: {self.action}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exits the context block, logging success or error based on execution result.

        Args:
            exc_type: Exception type if any.
            exc_value: Exception message if any.
            traceback: Exception traceback.

        Returns:
            bool: False to allow exceptions to propagate outside the context.
        """
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
        """
        Returns a formatted current timestamp for log entries.

        Returns:
            str: Current timestamp in 'YYYY-MM-DD HH:MM:SS' format.
        """
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write_log(self, message: str):
        """
        Writes a log message to the log file with a timestamp.

        Args:
            message (str): Log message to write.
        """
        if self._log_handle is None:
            raise RuntimeError("Log handle not initialized.")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log_handle.write(f"[{timestamp}] {message}\n")
        
    def log(self, message: str):
        """
        Logs a custom message with a 📝 prefix.

        Args:
            message (str): Message to log.
        """
        if self._log_handle:
            self._write_log(f"📝 {message}")
            print(f"📝 [{self._timestamp()}] {message}")