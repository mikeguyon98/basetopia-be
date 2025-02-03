from langchain_core.tools import tool
from app.ml.vector_db import get_vector_store, get_players_vector_store

from typing import List, Dict
from google.cloud import firestore

@tool
def get_highlight_docs(string_query: str) -> List[Dict]:
    """Fetches highlight documents based on a query."""
    print("Running get_highlight_docs tool")
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(string_query, k=5)
    print("docs")
    print(docs)
    highlights = []
    for doc in docs:
        highlights.append({
            "video_url": doc.metadata.get("video_url"),
            "description": doc.page_content
        })
    print("returning highlights")
    print(highlights)
    return highlights

@tool
def get_team_highlights(team_name: str, k: int = 5) -> List[Dict]:
    """Fetches highlights for a specific team."""
    print("Running get_team_highlights tool")
    highlights_ref = firestore.Client().collection("highlights")
    highlight_docs = (
        highlights_ref
        .where("team", "!=", None)
        .where("team.mlb_shortName", "==", team_name)
        .limit(k)
        .stream()
    )
    highlights = []
    for doc in highlight_docs:
        data = doc.to_dict()
        highlights.append({
            "video_url": data.get("video_url"),
            "description": data.get("description")
        })
    return highlights

@tool
def get_team_names() -> List[str]:
    """Returns a list of MLB team names."""
    db = firestore.Client()
    team_ref = db.collection("teams")
    return [doc.to_dict()["mlb_shortName"] for doc in team_ref.stream()]

@tool
def get_team_id(team_name: str) -> str:
    """Returns the id of a team."""
    db = firestore.Client()
    team_ref = db.collection("teams")
    return [doc.to_dict()["id"] for doc in team_ref.stream() if doc.to_dict()["mlb_shortName"] == team_name][0]

@tool
def get_player_id(player_name: str) -> str:
    """Returns the id of a player."""
    db = firestore.Client()
    player_ref = db.collection("players")
    return [doc.to_dict()["id"] for doc in player_ref.stream() if doc.to_dict()["name"] == player_name][0]

@tool
def is_valid_player(player_name: str) -> bool:
    """Checks if a player name is valid."""
    print("Running is_valid_player tool")
    if player_name in get_player_names():
        return True
    else:
        return False

@tool
def is_valid_team(team_name: str) -> bool:
    """Checks if a team name is valid."""
    print("Running is_valid_team tool")
    if team_name in get_team_names():
        return True
    else:
        return False
    
@tool
def get_similar_players(player_name: str) -> List[str]:
    """Returns a list of similar players to the given player name."""
    vector_store = get_players_vector_store()
    docs = vector_store.similarity_search(player_name, k=5)
    return [doc.metadata.get("player_name") for doc in docs]


# def get_model():
#     return ChatOpenAI(model="gpt-4o-mini", temperature=0)
# # 