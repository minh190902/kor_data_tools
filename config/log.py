import logging
import sys
import os

# Force unbuffered output for Docker
os.environ['PYTHONUNBUFFERED'] = '1'

# Global flag to prevent duplicate logger setup
_LOGGERS_INITIALIZED = False
_COMPONENT_LOGGERS = {}

# Create main logger
logger = logging.getLogger(__name__)

# Helper function for Docker-compatible logging
def log_and_flush(logger_instance, level: str, message: str):
    """Log message and immediately flush for Docker visibility"""
    getattr(logger_instance, level.lower())(message)
    sys.stdout.flush()

def get_logger(name: str) -> logging.Logger:
    """Get a logger with consistent configuration - cached to prevent duplicates"""
    global _COMPONENT_LOGGERS
    
    if name in _COMPONENT_LOGGERS:
        return _COMPONENT_LOGGERS[name]
    
    component_logger = logging.getLogger(name)
    component_logger.setLevel(logging.INFO)
    
    # Prevent propagation to avoid duplicate messages
    component_logger.propagate = False
    
    # Only add handlers if none exist
    if not component_logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        component_logger.addHandler(console_handler)
    
    _COMPONENT_LOGGERS[name] = component_logger
    return component_logger

# Create component-specific loggers (cached)
TOPIK_PROCESSOR_LOGGER = get_logger('TOPIK_PROCESSOR')
OCR_LOGGER = get_logger('OCR_PROCESSOR')
STRUCTURER_LOGGER = get_logger('STRUCTURER')