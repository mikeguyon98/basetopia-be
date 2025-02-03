# app/scripts/create_test_user.py
import firebase_admin
from firebase_admin import auth, credentials
import os
from pathlib import Path
from dotenv import load_dotenv

# Get root directory
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env.test')

# Initialize Firebase Admin
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
try:
    # Make sure we use the full path relative to root
    cred_path = os.path.join(ROOT_DIR, FIREBASE_CREDENTIALS_PATH)
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin initialized successfully")
except Exception as e:
    print(f"Failed to initialize Firebase: {e}")
    raise


def create_fresh_token():
    uid = os.getenv('TEST_USER_UID')
    if not uid:
        raise ValueError("No TEST_USER_UID in .env.test")

    custom_token = auth.create_custom_token(uid)
    print(f"Created custom token for UID: {uid}")

    # Update .env.test
    with open(ROOT_DIR / '.env.test', 'r') as file:
        lines = file.readlines()

    with open(ROOT_DIR / '.env.test', 'w') as file:
        token_written = False
        for line in lines:
            if line.startswith('TEST_USER_CUSTOM_TOKEN='):
                file.write(f'TEST_USER_CUSTOM_TOKEN={custom_token.decode()}\n')
                token_written = True
            else:
                file.write(line)
        if not token_written:
            file.write(f'\nTEST_USER_CUSTOM_TOKEN={custom_token.decode()}\n')

    return custom_token


if __name__ == "__main__":
    print("Creating fresh custom token...")
    token = create_fresh_token()
    print("New custom token created and saved to .env.test")
