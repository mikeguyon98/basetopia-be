import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

def initialize_counter(db):
    """
    Initialize the 'posts' counter document with a count of zero.
    """
    try:
        counter_doc_ref = db.collection('counters').document('posts')
        counter_doc_ref.set({'count': 0})
        print("Counter initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize counter: {str(e)}")

if __name__ == "__main__":
    load_dotenv()
    print("PRINTING CREDS")
    print(os.getenv('FIREBASE_CREDENTIALS_PATH'))
    cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
    firebase_admin.initialize_app(cred)

    # Get a reference to the Firestore client
    db = firestore.client()
    initialize_counter(db)