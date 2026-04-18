import logging
from . import state

class BufferedLogHandler(logging.Handler):
    def emit(self, record):
        try:
            level = record.levelname
            name = record.name
            message = self.format(record)
            state.add_log(level, name, message)
        except Exception:
            pass

def setup_logging(debug_mode=False):
    level = logging.DEBUG if debug_mode else logging.INFO
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    buffer_handler = BufferedLogHandler()
    buffer_handler.setLevel(logging.DEBUG)
    buffer_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(buffer_handler)
    
    return root_logger
