import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from flask import request, jsonify, session, current_app
import json
import os
from config import Config

# Initialize Firebase Admin SDK
firebase_app = None
config = Config()

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global firebase_app

    if firebase_app:
        return firebase_app

    try:
        # Check if Firebase credentials are available
        if not all([
            config.FIREBASE_PROJECT_ID,
            config.FIREBASE_PRIVATE_KEY,
            config.FIREBASE_CLIENT_EMAIL
        ]):
            print("⚠️  Firebase credentials not found - Firebase auth disabled")
            return None

        # Create credentials from environment variables
        cred_dict = {
            "type": "service_account",
            "project_id": config.FIREBASE_PROJECT_ID,
            "private_key": config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": config.FIREBASE_CLIENT_EMAIL,
            "client_id": config.FIREBASE_CLIENT_ID,
            "auth_uri": config.FIREBASE_AUTH_URI,
            "token_uri": config.FIREBASE_TOKEN_URI,
        }

        cred = credentials.Certificate(cred_dict)
        firebase_app = firebase_admin.initialize_app(cred)

        print(f"✅ Firebase initialized for project: {config.FIREBASE_PROJECT_ID}")
        return firebase_app

    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return None


def verify_firebase_token(id_token):
    """Verify Firebase ID token and return user info"""
    try:
        print(f"🔥 Starting Firebase token verification (token length: {len(id_token) if id_token else 0})")

        if not id_token:
            print(f"❌ No token provided")
            return None

        if not firebase_app:
            print(f"🔥 Firebase app not initialized, initializing...")
            init_result = init_firebase()
            if not init_result:
                print(f"❌ Firebase initialization failed")
                return None

        if not firebase_app:
            print(f"❌ Firebase app still not available after init attempt")
            return None

        print(f"🔥 Firebase app available, verifying token...")

        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        print(f"✅ Token verified successfully")
        print(f"🔥 Token claims: uid={decoded_token.get('uid')}, email={decoded_token.get('email')}, name={decoded_token.get('name')}")

        # Get additional user info from Firebase Admin SDK
        uid = decoded_token['uid']
        try:
            user_record = auth.get_user(uid)
            display_name = user_record.display_name
            profile_picture = user_record.photo_url
            print(f"🔥 User record retrieved: display_name={display_name}")
        except Exception as e:
            print(f"⚠️ Could not get user record: {e}")
            display_name = decoded_token.get('name')
            profile_picture = decoded_token.get('picture')

        user_info = {
            'firebase_uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'display_name': display_name,
            'profile_picture': profile_picture
        }

        print(f"✅ User info extracted successfully: email={user_info['email']}, verified={user_info['email_verified']}")
        return user_info

    except auth.InvalidIdTokenError as e:
        print(f"❌ Invalid Firebase token: {e}")
        return None
    except auth.ExpiredIdTokenError as e:
        print(f"❌ Expired Firebase token: {e}")
        return None
    except Exception as e:
        print(f"❌ Firebase token verification failed: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return None


def require_firebase_auth(f):
    """Decorator to require Firebase authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if Firebase is available
        if not firebase_app:
            init_firebase()

        if not firebase_app:
            # Fallback to old password auth if Firebase not available
            if not session.get('authenticated', False):
                return jsonify({'error': 'Authentication required'}), 401
            return f(*args, **kwargs)

        # Get ID token from request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            # Check session for fallback compatibility
            if session.get('firebase_user'):
                return f(*args, **kwargs)
            return jsonify({'error': 'Authorization header required'}), 401

        id_token = auth_header.split('Bearer ')[1]

        # Verify token
        user_info = verify_firebase_token(id_token)
        if not user_info:
            return jsonify({'error': 'Invalid token'}), 401

        # Store user info in request context
        request.firebase_user = user_info

        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """Get current authenticated user info"""
    # Try Firebase user first
    if hasattr(request, 'firebase_user'):
        return request.firebase_user

    # Fallback to session
    if session.get('firebase_user'):
        return session['firebase_user']

    return None


def is_firebase_available():
    """Check if Firebase is properly configured and available"""
    return firebase_app is not None