"""
Pytest configuration and fixtures for AI Interview System tests.
"""
import pytest
import os
import sys
import tempfile
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    from flask import Flask
    from flask_cors import CORS
    
    # Create test app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JSON_SORT_KEYS'] = False
    
    # Configure CORS for testing
    CORS(app)
    
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    import sqlite3
    
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Initialize the test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'candidate',
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            resume_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            job_description TEXT NOT NULL,
            mode TEXT DEFAULT 'ai',
            created_by INTEGER,
            status TEXT DEFAULT 'pending',
            warnings_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def sample_interview_data():
    """Sample interview data for testing."""
    return {
        'interview_id': 'test_interview_123',
        'full_name': 'Test User',
        'email': 'test@example.com',
        'job_description': 'Software Engineer',
        'resume_text': 'Test resume content',
        'personality': 'friendly',
        'status': 'created',
        'questions': [
            {
                'id': 1,
                'text': 'Tell me about yourself',
                'category': 'introduction',
                'difficulty': 'easy'
            },
            {
                'id': 2,
                'text': 'What are your strengths?',
                'category': 'technical',
                'difficulty': 'medium'
            }
        ],
        'answers': [],
        'violations': [],
        'warnings': 0,
        'emotion_timeline': []
    }


@pytest.fixture
def temp_interview_file(sample_interview_data):
    """Create a temporary interview JSON file."""
    import tempfile
    
    fd, path = tempfile.mkstemp(suffix='.json', dir='interviews')
    
    with os.fdopen(fd, 'w') as f:
        json.dump(sample_interview_data, f)
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)
