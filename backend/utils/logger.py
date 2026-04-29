"""
Logging configuration for the AI Interview System.
Provides structured logging with different levels and handlers.
"""
import logging
import os
from datetime import datetime


def setup_logger(name: str = 'interview_system', level: int = None) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        name: Logger name (default: 'interview_system')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    if level is None:
        level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # File handler for errors (WARNING and above) 
    log_dir = os.getenv('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    error_file_handler = logging.FileHandler(
        os.path.join(log_dir, f'error_{datetime.now().strftime("%Y%m%d")}.log'),
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.WARNING)
    error_file_handler.setFormatter(detailed_formatter)

    # File handler for all logs (DEBUG and above) 
    all_file_handler = logging.FileHandler(
        os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log'),
        encoding='utf-8'
    )
    all_file_handler.setLevel(logging.DEBUG)
    all_file_handler.setFormatter(detailed_formatter)

    # Add handlers to logger  
    logger.addHandler(console_handler)  
    logger.addHandler(error_file_handler)  
    logger.addHandler(all_file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get an existing or new logger."""
    if name is None:
        name = 'interview_system'
    return logging.getLogger(name)


class RequestLogger:
    """Middleware-like class to log HTTP requests."""
    
    def __init__(self):
        self.logger = get_logger('request')
        
    def log_request(self, method: str, path: str, status_code: int = None, duration_ms: float = None):
        """Log an HTTP request."""
        msg = f"{method} {path}"
        if status_code:
            msg += f" -> {status_code}"
        if duration_ms is not None:
            msg += f" ({duration_ms:.2f}ms)"
        
        if status_code and status_code >= 500:
            self.logger.error(msg)  
        elif status_code and status_code >= 400:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def log_error(self, method: str, path: str, exception: Exception):
        """Log an exception during request processing."""
        self.logger.error(
            f"{method} {path} -> Error: {type(exception).__name__}: {str(exception)}",
            exc_info=True
        )


# Convenience functions for common operations  

def log_interview_event(event_type: str, interview_id: str, **kwargs):
    """Log interview-related events.""" 
    logger = get_logger('interview')
    msg = f"[{event_type}] Interview: {interview_id}"
    if kwargs:
        for k, v in kwargs.items():
            msg += f", {k}: {v}"

    if event_type in ['created', 'started', 'completed']:
        logger.info(msg)
    elif event_type in ['violation', 'warning']:
        logger.warning(msg)
    else:
        logger.debug(msg)


def log_db_operation(operation: str, table_name: str, **kwargs):
    """Log database operations."""
    logger = get_logger('database')
    msg = f"[{operation}] Table: {table_name}"
    if kwargs:
        for k, v in kwargs.items():
            msg += f", {k}: {v}"
    logger.debug(msg)


# Default loggers for easy import  
app_logger = setup_logger('app')
api_logger = setup_logger('api')
db_logger = setup_logger('database')
