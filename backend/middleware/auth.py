from functools import wraps
from flask import request, jsonify
from database.models import User

def require_auth(f):
    """Decorator to verify authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Missing authorization header'
            }), 401
        
        try:
            token_parts = auth_header.split()
            if len(token_parts) != 2 or token_parts[0] != 'Bearer':
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid authorization header format'
                }), 401
            
            user_id = int(token_parts[1])
            user = User.get_by_id(user_id)
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 401
            
            request.current_user = user
            return f(*args, **kwargs)
        
        except (ValueError, IndexError, AttributeError) as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid authorization token'
            }), 401
    
    return decorated

def require_admin(f):
    """Decorator to verify admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Missing authorization header'
            }), 401
        
        try:
            token_parts = auth_header.split()
            if len(token_parts) != 2 or token_parts[0] != 'Bearer':
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid authorization header format'
                }), 401
            
            user_id = int(token_parts[1])
            user = User.get_by_id(user_id)
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 401
            
            if user['role'] != 'admin':
                return jsonify({
                    'status': 'error',
                    'message': 'Admin access required'
                }), 403
            
            request.current_user = user
            return f(*args, **kwargs)
        
        except (ValueError, IndexError, AttributeError) as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid authorization token'
            }), 401
    
    return decorated
