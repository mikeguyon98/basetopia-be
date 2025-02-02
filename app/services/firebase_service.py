from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime
from typing import Optional

class FirebaseService:
    def __init__(self):
        self.db = firestore.client()
        self.users_collection = self.db.collection('users')
        self.highlights_collection = self.db.collection('highlights')
        self.posts_collection = self.db.collection('posts')

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

    # ### New Methods Added Below ###
    async def save_highlight_post(self, highlight_data: dict, user_email: str) -> str:
        """
        Save a highlight post to the 'posts' collection in Firebase with an autoincrementing ID.

        Args:
            highlight_data (dict): The highlight data to be saved.

        Returns:
            str: The autoincremented document ID.
        """
        try:
            from firebase_admin import firestore

            highlight_data['created_at'] = datetime.now()

            # Reference to the counter document
            counter_doc_ref = self.db.collection('counters').document('posts')

            # Atomically increment the counter
            counter_doc_ref.update({'count': firestore.Increment(1)})

            # Get the new counter value
            counter_snapshot = counter_doc_ref.get()
            new_counter_value = counter_snapshot.get('count')
            if highlight_data.get("player_tags") is None:
                highlight_data["player_tags"] = []
            if highlight_data.get("team_tags") is None:
                highlight_data["team_tags"] = []
            highlight_data["user_email"] = user_email
            # Set the new post with the autoincremented ID
            post_id = str(new_counter_value)
            post_doc_ref = self.posts_collection.document(post_id)
            post_doc_ref.set(highlight_data)

            return post_id

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save highlight: {str(e)}")

    async def get_paginated_highlights(self, page_size: int, last_cursor: Optional[dict] = None) -> dict:
        """
        Retrieve paginated highlights using cursor-based pagination.

        Args:
            page_size (int): Number of items per page.
            last_cursor (Optional[dict]): Dictionary containing 'id' of the last item from the previous page.

        Returns:
            dict: Contains 'data' and 'next_page_cursor'.
        """
        try:
            # Order the posts by 'id' in ascending order (since IDs are autoincremented)
            query = self.posts_collection.order_by('id', direction=firestore.Query.ASCENDING)
            
            # If a cursor is provided, start after it
            if last_cursor:
                last_id = last_cursor['id']
                query = query.start_after({'id': last_id})
            
            # Limit the results to the page size
            query = query.limit(page_size)
            
            # Fetch the documents for the current page
            docs = query.stream()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id  # Include the ID in the data
                data.append(doc_data)
                
            # Get the 'id' of the last document for the next page cursor
            if data:
                last_doc = data[-1]
                next_page_cursor = {
                    'id': last_doc['id']
                }
            else:
                next_page_cursor = None
                
            return {
                "data": data,
                "next_page_cursor": next_page_cursor
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve highlights: {str(e)}")
        
    async def get_post_by_id(self, post_id: str):
        doc_ref = self.posts_collection.document(post_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Post not found")
        return doc.to_dict()
    
    async def get_posts_by_player_tag(self, tag: str):
        query = self.posts_collection.where('player_tags', 'array_contains', tag)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    async def get_posts_by_team_tag(self, tag: str):
        query = self.posts_collection.where('team_tags', 'array_contains', tag)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
