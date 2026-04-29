"""
Unit tests for backup functionality.
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBackupManager:
    """Test cases for backup manager."""
    
    def test_backup_manager_init(self):
        """Test backup manager initialization."""
        from utils.backup import BackupManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(db_path=':memory:', backup_dir=tmpdir)
            assert bm.backup_dir == tmpdir
    
    def test_list_backups_empty(self):
        """Test listing backups when none exist."""
        from utils.backup import BackupManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(backup_dir=tmpdir)
            backups = bm.list_backups()
            assert backups == []
    
    def test_create_backup_no_db(self):
        """Test creating backup when no database exists."""
        from utils.backup import BackupManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            bm = BackupManager(db_path='/nonexistent/db.db', backup_dir=tmpdir)
            result = bm.create_backup()
            assert result['status'] == 'error'
            assert 'not found' in result['message'].lower()


class TestConfigValidation:
    """Test cases for configuration validation."""
    
    def test_config_class_exists(self):
        """Test that Config class exists."""
        from config import Config
        assert Config is not None
    
    def test_config_defaults(self):
        """Test default configuration values."""
        from config import Config
        
        assert Config.DATABASE_PATH == 'interviews.db'
        assert Config.MAX_WARNINGS == 3
        assert Config.QUESTIONS_PER_INTERVIEW == 5
        assert Config.LOG_LEVEL == 'INFO'
    
    def test_validate_environment_missing_vars(self):
        """Test environment validation with missing required vars."""
        from config import validate_environment
        
        # This should work even without required vars in test environment
        is_valid, missing = validate_environment()
        # May pass or fail depending on whether vars are set
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
    
    def test_get_cors_origins(self):
        """Test getting configured CORS origins."""
        from config import get_configured_cors_origins
        
        origins = get_configured_cors_origins()
        assert isinstance(origins, list)


class TestLoggerSetup:
    """Test cases for logging setup."""
    
    def test_setup_logger(self):
        """Test logger setup."""
        from utils.logger import setup_logger
        
        logger = setup_logger('test_logger')
        assert logger is not None
        assert logger.name == 'test_logger'
    
    def test_get_logger(self):
        """Test getting existing logger."""
        from utils.logger import get_logger
        
        logger = get_logger('test_get_logger')
        assert logger is not None
    
    def test_log_interview_event(self):
        """Test logging interview events."""
        from utils.logger import log_interview_event
        
        # Should not raise exception
        log_interview_event('created', 'test_id', name='Test')
    
    def test_log_db_operation(self):
        """Test logging database operations."""
        from utils.logger import log_db_operation
        
        # Should not raise exception
        log_db_operation('INSERT', 'users', rows=1)
