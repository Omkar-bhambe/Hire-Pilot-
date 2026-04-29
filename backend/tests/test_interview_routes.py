"""
Unit tests for interview routes.
"""
import pytest
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInterviewRoutes:
    """Test cases for interview endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_root_endpoint(self, client):
        """Test API root endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'version' in data
    
    def test_404_error(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert data['error'] == 'not_found'


class TestInterviewCreation:
    """Test cases for interview creation."""
    
    def test_create_interview_missing_fields(self, client):
        """Test creating interview with missing required fields."""
        response = client.post(
            '/api/interview/create',
            json={}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_create_interview_invalid_json(self, client):
        """Test creating interview with invalid JSON."""
        response = client.post(
            '/api/interview/create',
            data='not valid json',
            content_type='application/json'
        )
        assert response.status_code == 500


class TestInterviewStatus:
    """Test cases for interview status."""
    
    def test_get_status_not_found(self, client):
        """Test getting status of non-existent interview."""
        response = client.get('/api/interview/nonexistent_id/status')
        assert response.status_code == 404


class TestInterviewAnswers:
    """Test cases for submitting answers."""
    
    def test_submit_answer_not_found(self, client):
        """Test submitting answer to non-existent interview."""
        response = client.post(
            '/api/interview/nonexistent_id/answer',
            json={'question_index': 0, 'answer': 'Test answer'}
        )
        assert response.status_code == 404
    
    def test_submit_answer_empty(self, client):
        """Test submitting empty answer."""
        response = client.post(
            '/api/interview/test_id/answer',
            json={'question_index': 0, 'answer': ''}
        )
        # Either 404 (interview not found) or 400 (empty answer)
        assert response.status_code in [400, 404]


class TestInterviewCompletion:
    """Test cases for completing interviews."""
    
    def test_complete_interview_not_found(self, client):
        """Test completing non-existent interview."""
        response = client.post('/api/interview/nonexistent_id/complete')
        assert response.status_code == 404
