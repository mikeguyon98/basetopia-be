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
        self.docs_collection = self.db.collection('docs')
        self.players_collection = self.db.collection('players')
        self.teams_collection = self.db.collection('teams')

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

    async def get_all_posts(self):
        query = self.posts_collection.order_by(
            'id', direction=firestore.Query.ASCENDING)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]

    # ### New Methods Added Below ###
    async def save_highlight_post(self, highlight_data: dict, user_email: str) -> str:
        """
        Save a highlight post to the 'posts' collection in Firebase with an autoincrementing ID.

        Args:
            highlight_data (dict): The highlight data to be saved.
            user_email (str): The email of the user saving the highlight.

        Returns:
            str: The autoincremented document ID.
        """
        try:
            from firebase_admin import firestore

            # Set the created_at timestamp
            highlight_data['created_at'] = datetime.now()

            # Reference to the counter document and increment atomically
            counter_doc_ref = self.db.collection('counters').document('posts')
            counter_doc_ref.update({'count': firestore.Increment(1)})

            # Get the new counter value
            counter_snapshot = counter_doc_ref.get()
            new_counter_value = counter_snapshot.get('count')

            # Ensure tags have default empty list if not provided
            if highlight_data.get("player_tags") is None:
                highlight_data["player_tags"] = []
            if highlight_data.get("team_tags") is None:
                highlight_data["team_tags"] = []

            highlight_data["user_email"] = user_email

            # **Add the auto-incremented ID into the document data**
            highlight_data["id"] = new_counter_value

            # Use the new counter value as the document id (converted to string)
            post_id = str(new_counter_value)
            post_doc_ref = self.posts_collection.document(post_id)
            post_doc_ref.set(highlight_data)

            return post_id

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to save highlight: {str(e)}")

    async def update_highlight_post(self, post_id: str, highlight_data: dict, user_email: str) -> str:
        """
        Update a highlight post.
        """
        get_post = await self.get_post_by_id(post_id)
        if get_post["user_email"] != user_email:
            raise HTTPException(
                status_code=403, detail="You are not allowed to update this post")
        post_doc_ref = self.posts_collection.document(post_id)
        post_doc_ref.update(highlight_data)
        return post_id

    async def get_paginated_highlights(self, page_size: int, last_cursor: Optional[dict] = None) -> dict:
        """
        Retrieve paginated highlights using cursor-based pagination.

        Args:
            page_size (int): Number of items per page.
            last_cursor (Optional[dict]): Dict containing 'created_at' and 'id' of the last item from previous page.

        Returns:
            dict: Contains 'data' (list of posts) and 'next_page_cursor'.
        """
        try:
            # Order by 'created_at' first and then 'id' as a tie-breaker
            query = self.posts_collection.order_by('created_at', direction=firestore.Query.ASCENDING) \
                .order_by('id', direction=firestore.Query.ASCENDING)

            # If a cursor is provided, start after the last document using both fields
            if last_cursor:
                query = query.start_after(
                    last_cursor['created_at'], last_cursor['id'])

            # Limit the results to the page size
            query = query.limit(page_size)

            docs = query.stream()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                # Ensure the 'id' field is in the returned data.
                doc_data['id'] = doc_data.get('id') or doc.id
                data.append(doc_data)

            # Prepare next_page_cursor for response if there is at least one document
            if data:
                last_doc = data[-1]
                next_page_cursor = {
                    'created_at': last_doc['created_at'],
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

        return {"data": results, "next_page_cursor": next_cursor}

    async def get_post_by_id(self, post_id: str):
        doc_ref = self.posts_collection.document(post_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Post not found")
        return doc.to_dict()

    async def get_posts_by_player_tag(self, tag: str):
        query = self.posts_collection.where(
            'player_tags', 'array_contains', tag)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]

    async def get_posts_by_team_tag(self, tag: str):
        query = self.posts_collection.where('team_tags', 'array_contains', tag)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]

    async def search_posts(self, query: str):
        query_lower = query.lower()

        #########################
        # Teams and players via local filtering
        #########################

        # 1. Get *all* team documents (since there are only 30 MLB teams).
        teams_docs = list(self.teams_collection.stream())

        # 2. Filter them in Python by checking if the query is in either mlb_name or mlb_locationName
        matched_teams = []
        for doc in teams_docs:
            team_data = doc.to_dict()
            # Make sure you gracefully handle missing fields if needed
            name = team_data.get("mlb_name", "").lower()
            location = team_data.get("mlb_locationName", "").lower()
            if query_lower in name or query_lower in location:
                matched_teams.append(team_data)

        # 3. Get *all* player documents
        players_docs = list(self.players_collection.stream())

        # 4. Filter them similarly
        matched_players = []
        for doc in players_docs:
            player_data = doc.to_dict()
            full_name = player_data.get("mlb_person_fullName", "").lower()
            if query_lower in full_name:
                matched_players.append(player_data)

        #########################
        # If you still want posts by prefix-search, keep your old approach:
        #########################

        posts_query = self.posts_collection.order_by('title') \
            .start_at([query_lower]).end_at([query_lower + '\uf8ff'])
        posts_docs = list(posts_query.stream())

        return {
            "players": matched_players,
            "teams": matched_teams,
            "posts": [doc.to_dict() for doc in posts_docs],
        }
    
    async def get_player_by_id(self, player_id: str):
        doc_ref = self.players_collection.document(player_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Player not found")
        return doc.to_dict()
    
    async def get_all_players(self):
        docs = self.players_collection.stream()
        return [doc.to_dict() for doc in docs]
    
    async def get_team_by_id(self, team_id: str):
        doc_ref = self.teams_collection.document(team_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Team not found")
        return doc.to_dict()
    
    async def get_all_teams(self):
        docs = self.teams_collection.stream()
        return [doc.to_dict() for doc in docs]
    
    async def get_last_30_game_ids(self):
        docs = self.docs_collection.order_by('game_id', direction=firestore.Query.DESCENDING).limit(30).stream()
        return [doc.to_dict() for doc in docs]
