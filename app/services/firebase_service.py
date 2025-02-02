from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional


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
    async def save_highlight_post(self, highlight_data: dict) -> str:
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

            # Set the new post with the autoincremented ID
            post_id = str(new_counter_value)
            post_doc_ref = self.posts_collection.document(post_id)
            post_doc_ref.set(highlight_data)

            return post_id

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to save highlight: {str(e)}")

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
            query = self.posts_collection.order_by(
                'id', direction=firestore.Query.ASCENDING)

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
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve highlights: {str(e)}")

    async def get_user_posts(self, user_id: str, page_size: int, last_cursor: Optional[dict] = None):
        query = self.db.collection('posts').where('user_email', '==', user_id)
        return await self._paginate_posts(query, page_size, last_cursor)

    async def get_team_posts(self, team_ids: List[str], page_size: int, last_cursor: Optional[dict] = None):
        query = self.db.collection('posts').where(
            'team_tags', 'array_contains_any', team_ids)
        return await self._paginate_posts(query, page_size, last_cursor)

    async def get_player_posts(self, player_ids: List[str], page_size: int, last_cursor: Optional[dict] = None):
        query = self.db.collection('posts').where(
            'player_tags', 'array_contains_any', player_ids)
        return await self._paginate_posts(query, page_size, last_cursor)

    async def _paginate_posts(self, query, page_size: int, last_cursor: Optional[dict] = None):
        # Add ordering to query
        query = query.order_by(
            'created_at', direction=firestore.Query.DESCENDING)

        # Apply cursor if provided
        if last_cursor:
            query = query.start_after({
                'created_at': last_cursor['created_at'],
                'id': last_cursor['id']
            })

        # Fetch one extra document to determine if there are more results
        docs = query.limit(page_size + 1).stream()

        # Convert to list to handle pagination
        results = []
        for doc in docs:
            results.append({**doc.to_dict(), 'id': doc.id})

        # Determine if there are more results and remove the extra document
        has_more = len(results) > page_size
        if has_more:
            results.pop()

        # Create the next cursor if there are more results
        next_cursor = None
        if has_more and results:
            last_doc = results[-1]
            next_cursor = {
                'created_at': last_doc['created_at'],
                'id': last_doc['id']
            }

        return {
            "data": results,
            "next_page_cursor": next_cursor
        }
