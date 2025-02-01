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

    async def get_searchable_players(self):
        try:
            players_ref = self.db.collection('players')
            docs = players_ref.stream()

            return [{
                "id": doc.get("id"),
                "name": doc.get("mlb_person_fullName"),
                "metadata": {
                    "jersey_number": doc.get("mlb_jerseyNumber"),
                    "position": {
                        "name": doc.get("mlb_position_name"),
                        "abbreviation": doc.get("mlb_position_abbreviation"),
                        "type": doc.get("mlb_position_type")
                    },
                    "status": doc.get("mlb_status_description"),
                    "mlb_id": doc.get("mlb_person_id"),
                    "team_id": doc.get("team_id")
                }
            } for doc in docs]
        except Exception as e:
            raise Exception(f"Failed to get players: {str(e)}")

    async def get_searchable_teams(self):
        try:
            teams_ref = self.db.collection('teams')
            docs = teams_ref.stream()

            return [{
                "id": doc.get("id"),
                "name": doc.get("mlb_name"),
                "metadata": {
                    "location": doc.get("mlb_locationName"),
                    "short_name": doc.get("mlb_shortName"),
                    "team_name": doc.get("mlb_teamName"),
                    "abbreviation": doc.get("mlb_abbreviation"),
                    "mlb_id": doc.get("mlb_id"),
                    "season": doc.get("mlb_season"),
                    "spring_league": {
                        "name": doc.get("mlb_springLeague_name"),
                        "abbreviation": doc.get("mlb_springLeague_abbreviation")
                    }
                }
            } for doc in docs]
        except Exception as e:
            raise Exception(f"Failed to get teams: {str(e)}")
