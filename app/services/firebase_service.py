from firebase_admin import firestore
from fastapi import HTTPException


class FirebaseService:
    def __init__(self):
        self.db = firestore.client()
        self.users_collection = self.db.collection('users')

    async def get_user(self, uid: str):
        doc_ref = self.users_collection.document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        return {**doc.to_dict(), "uid": uid}

    async def create_user(self, uid: str, user_data: dict):
        doc_ref = self.users_collection.document(uid)
        doc_ref.set(user_data)
        return {**user_data, "uid": uid}

    async def update_user(self, uid: str, user_data: dict):
        doc_ref = self.users_collection.document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")

        # Remove None values from update data
        update_data = {k: v for k, v in user_data.items() if v is not None}
        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        return {**updated_doc.to_dict(), "uid": uid}

    async def delete_user(self, uid: str):
        doc_ref = self.users_collection.document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        doc_ref.delete()
        return {"message": "User deleted successfully"}
