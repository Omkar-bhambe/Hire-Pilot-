"""
Configuration management for AI Interview System.
Validates required environment variables and provides configuration values.
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class Config:
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    
    # API keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyCWwFyiXXeqaRmb8xb5XvDIbd_nIbzNVE0')
    # OpenAI TTS
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')
    
    # Database settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'interviews.db')
    DATABASE_BACKUP_PATH = os.getenv('DATABASE_BACKUP_PATH', 'backups')
    
    # Interview settings
    MAX_WARNINGS = int(os.getenv('MAX_WARNINGS', '3'))
    QUESTIONS_PER_INTERVIEW = int(os.getenv('QUESTIONS_PER_INTERVIEW', '5'))
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    
    # Rate limiting
    RATE_LIMIT_DAY = os.getenv('RATE_LIMIT_DAY', '200')
    RATE_LIMIT_HOUR = os.getenv('RATE_LIMIT_HOUR', '50')
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(500 * 1024 * 1024)))  # 500MB default
    
    # JWT settings
    JWT_EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', '24'))
    
    # Backup settings
    AUTO_BACKUP_ENABLED = os.getenv('AUTO_BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))


# Required environment variables for production
REQUIRED_ENV_VARS: List[str] = [
    'GEMINI_API_KEY',
]

# Optional but recommended environment variables
RECOMMENDED_ENV_VARS: List[str] = [
    'FLASK_SECRET_KEY',
]


def validate_environment() -> tuple[bool, List[str]]:
    """
    Validate required environment variables.
    
    Returns:
        Tuple of (is_valid, missing_variables)
    """
    missing = []
    
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if not value or value == '':
            missing.append(var)
    
    return len(missing) == 0, missing


def get_configured_cors_origins() -> List[str]:
    """Get configured CORS origins, filtered for empty values."""
    return [origin.strip() for origin in Config.CORS_ORIGINS if origin.strip()]


def check_environment() -> None:
    """
    Check environment configuration and raise error if critical issues found.
    Should be called on application startup.
    """
    is_valid, missing = validate_environment()
    
    if not is_valid:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please set these variables in your .env file or environment."
        )
    
    # Check for debug/development settings in production
    if not Config.DEBUG and Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        import warnings
        warnings.warn(
            "SECRET_KEY is still set to default development value. "
            "This is not secure for production!"
        )
    
    # Create necessary directories
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    os.makedirs(Config.DATABASE_BACKUP_PATH, exist_ok=True)
    os.makedirs('interviews', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)


# Export config instance
config = Config
