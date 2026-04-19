import logging
from . import state

FILTERED_PATHS = ['/api/logs', '/snapshot']


class FilteredLogHandler(logging.Handler):
    """Handler that filters out noisy log messages."""
    
    def emit(self, record):
        try:
            if record.name == 'werkzeug':
                msg = record.getMessage()
                for path in FILTERED_PATHS:
                    if path in msg:
                        return
            
            level = record.levelname
            name = record.name
            message = self.format(record)
            state.add_log(level, name, message)
        except Exception:
            pass


class FilteredConsoleHandler(logging.StreamHandler):
    """Console handler that filters out noisy log messages."""
    
    def emit(self, record):
        try:
            if record.name == 'werkzeug':
                msg = record.getMessage()
                for path in FILTERED_PATHS:
                    if path in msg:
                        return
            super().emit(record)
        except Exception:
            pass


def setup_logging(debug_mode=False):
    level = logging.DEBUG if debug_mode else logging.INFO
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = FilteredConsoleHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    buffer_handler = FilteredLogHandler()
    buffer_handler.setLevel(logging.DEBUG)
    buffer_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(buffer_handler)
    
    return root_logger
