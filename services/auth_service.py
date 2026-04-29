import uuid
from services.database_service import db
from datetime import datetime
from werkzeug.security import check_password_hash

def request_registration(email, password, name):
    """Stores registration in a temporary 'pending' collection."""
    try:
        approval_token = str(uuid.uuid4())
        pending_ref = db.collection('pending_registrations').document(approval_token)
        pending_ref.set({
            "email": email,
            "name": name,
            "password": password, # Temporary plain text until approved
            "requested_at": datetime.now(),
            "status": "pending"
        })
        print(f"Data staged in cloud for: {email}")
        return approval_token

    except Exception as e:
        print(f"Cloud Storage Error: {e}")
        return None

def verify_login(email, password):
    """Verifies credentials against the approved Cloud Admins collection."""
    admin_ref = db.collection('admins').document(email).get()
    if admin_ref.exists:
        data = admin_ref.to_dict()
        # Compare provided password with stored cloud hash
        if check_password_hash(data['password_hash'], password):
            # Update last login in cloud
            db.collection('admins').document(email).update({
                "last_login": datetime.now()
            })
            return True, data
    return False, None