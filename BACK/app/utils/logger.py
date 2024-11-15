# app/utils/logger.py
import logging
import sys
import threading
import time
from colorama import Fore, Style, init as colorama_init
from contextlib import contextmanager

# Initialize colorama for colored output
colorama_init()

def create_custom_logger():
    custom_logger = logging.Logger("fastapi_app", level=logging.INFO)

    handler = SpinnerLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    custom_logger.addHandler(handler)

    return custom_logger

class SpinnerLogHandler(logging.StreamHandler):
    """Custom log handler with spinner animation and emoji on completion."""
    
    spinner_chars = ["|", "/", "-", "\\"]
    
    def __init__(self):
        super().__init__(sys.stdout)
        self._stop_spinner = threading.Event()
        self._spinner_thread = None

    def emit(self, record):
        """Start spinner on task start, then display an emoji on task completion."""
        message = self.format(record)
        
        log_color = self._get_color(record.levelno)
        level_name = f"{log_color}{record.levelname.upper()}{Style.RESET_ALL}:"
        formatted_level = f"{level_name:<18}"

        # Display spinner when task starts
        if message.endswith("..."):
            full_message = f"{formatted_level} {message}"
            self._stop_spinner.clear()
            self._spinner_thread = threading.Thread(target=self._animate_spinner, args=(full_message,))
            self._spinner_thread.start()
        else:
            self._stop_spinner.set()
            if self._spinner_thread:
                self._spinner_thread.join()
            sys.stdout.write(f"\r{formatted_level} {message} ✅\n")
            sys.stdout.flush()

    def _animate_spinner(self, message):
        idx = 0
        while not self._stop_spinner.is_set():
            sys.stdout.write(f"\r{message} {self.spinner_chars[idx % len(self.spinner_chars)]}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")

    def _get_color(self, level):
        if level == logging.INFO:
            return Fore.GREEN
        elif level == logging.WARNING:
            return Fore.YELLOW
        elif level == logging.ERROR:
            return Fore.RED
        return Style.RESET_ALL

logger = create_custom_logger()

@contextmanager
def log_task(message):
    logger.info(f"{message}...", extra={"end": ""})
    try:
        yield
        logger.info(message)
    except Exception:
        logger.error(message)
        raise
