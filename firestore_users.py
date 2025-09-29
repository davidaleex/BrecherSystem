import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import json
from config import Config

config = Config()

def get_firestore_client():
    """Get Firestore client instance"""
    if not firebase_admin._apps:
        from firebase_auth import init_firebase
        init_firebase()

    return firestore.client()

def create_user_profile(firebase_uid, email, display_name=None, profile_data=None):
    """Create or update user profile in Firestore"""
    try:
        db = get_firestore_client()

        # Base user data
        user_data = {
            'firebase_uid': firebase_uid,
            'email': email,
            'display_name': display_name,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'is_active': True
        }

        # Add extended profile data if provided
        if profile_data:
            user_data.update(profile_data)

        # Use merge=True to update existing document or create new one
        doc_ref = db.collection('users').document(firebase_uid)
        doc_ref.set(user_data, merge=True)

        print(f"✅ User profile created/updated in Firestore for: {email}")
        return user_data

    except Exception as e:
        print(f"❌ Failed to create user profile in Firestore: {e}")
        return None

def get_user_profile(firebase_uid):
    """Get user profile from Firestore"""
    try:
        db = get_firestore_client()
        doc_ref = db.collection('users').document(firebase_uid)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            print(f"✅ User profile loaded from Firestore: {data.get('email')}")
            return data
        else:
            print(f"❌ User profile not found in Firestore: {firebase_uid}")
            return None

    except Exception as e:
        print(f"❌ Failed to get user profile from Firestore: {e}")
        return None

def update_user_profile(firebase_uid, update_data):
    """Update specific fields in user profile"""
    try:
        db = get_firestore_client()
        doc_ref = db.collection('users').document(firebase_uid)

        # Add timestamp to update
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP

        doc_ref.update(update_data)
        print(f"✅ User profile updated in Firestore: {firebase_uid}")
        return True

    except Exception as e:
        print(f"❌ Failed to update user profile in Firestore: {e}")
        return False

def delete_user_profile(firebase_uid):
    """Delete user profile from Firestore"""
    try:
        db = get_firestore_client()
        doc_ref = db.collection('users').document(firebase_uid)
        doc_ref.delete()

        print(f"✅ User profile deleted from Firestore: {firebase_uid}")
        return True

    except Exception as e:
        print(f"❌ Failed to delete user profile from Firestore: {e}")
        return False

def get_all_users():
    """Get all user profiles from Firestore (admin function)"""
    try:
        db = get_firestore_client()
        users_ref = db.collection('users')
        docs = users_ref.stream()

        users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            users.append(user_data)

        print(f"✅ Retrieved {len(users)} users from Firestore")
        return users

    except Exception as e:
        print(f"❌ Failed to get all users from Firestore: {e}")
        return []