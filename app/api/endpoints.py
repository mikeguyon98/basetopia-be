from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated, Optional
from firebase_admin import auth
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.translator import VertexAITranslation
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.firebase_service import FirebaseService
from app.ml.endpoints import FinalResponse, NextPageCursor, router as ml_router
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from typing import List, Dict
import re

cloud_id = os.getenv("FIREBASE_PROJECT_ID", "basetopia-b9302")
router = APIRouter()
security = HTTPBearer()
translation_service = VertexAITranslation(project_id=cloud_id)
firebase_service = FirebaseService()


class SearchResult(BaseModel):
    id: str
    name: str
    type: str
    metadata: dict
    score: int


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    nationality: str
    teams_following: List[str] = []
    players_following: List[str] = []


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    nationality: Optional[str] = None
    teams_following: Optional[List[str]] = None
    players_following: Optional[List[str]] = None


class UserResponse(UserBase):
    uid: str


class TranslationRequest(BaseModel):
    content: str
    target_language: str
    input_language: Optional[str] = None


class TranslationDictRequest(BaseModel):
    data: dict
    target_language: str
    fields_to_translate: list


class PostsResponse(BaseModel):
    posts: List[FinalResponse]
    next_page_cursor: Optional[NextPageCursor]
    page_size: int


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/posts/me", response_model=PostsResponse)
async def get_user_posts(
    token_data: dict = Depends(verify_firebase_token),
    page_size: int = Query(10, ge=1, le=100),
    last_created_at: Optional[str] = Query(None),
    last_id: Optional[str] = Query(None)
):
    """Get posts created by the current user"""
    try:
        uid = token_data["uid"]

        last_cursor = None
        if last_created_at and last_id:
            last_cursor = {
                'created_at': datetime.fromisoformat(last_created_at),
                'id': last_id
            }

        results = await firebase_service.get_user_posts(
            user_id=uid,
            page_size=page_size,
            last_cursor=last_cursor
        )

        next_page_cursor = None
        if results["next_page_cursor"]:
            next_page_cursor = {
                'created_at': results["next_page_cursor"]['created_at'].isoformat(),
                'id': results["next_page_cursor"]['id']
            }

        return PostsResponse(
            posts=results["data"],
            next_page_cursor=next_page_cursor,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/following/teams", response_model=PostsResponse)
async def get_team_posts(
    token_data: dict = Depends(verify_firebase_token),
    page_size: int = Query(10, ge=1, le=100),
    last_created_at: Optional[str] = Query(None),
    last_id: Optional[str] = Query(None)
):
    """Get posts for teams the user follows"""
    try:
        uid = token_data["uid"]
        user_data = await firebase_service.get_user(uid)
        teams_following = user_data["teams_following"]

        last_cursor = None
        if last_created_at and last_id:
            last_cursor = {
                'created_at': datetime.fromisoformat(last_created_at),
                'id': last_id
            }

        results = await firebase_service.get_team_posts(
            team_ids=teams_following,
            page_size=page_size,
            last_cursor=last_cursor
        )

        next_page_cursor = None
        if results["next_page_cursor"]:
            next_page_cursor = {
                'created_at': results["next_page_cursor"]['created_at'].isoformat(),
                'id': results["next_page_cursor"]['id']
            }

        return PostsResponse(
            posts=results["data"],
            next_page_cursor=next_page_cursor,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/following/players", response_model=PostsResponse)
async def get_player_posts(
    token_data: dict = Depends(verify_firebase_token),
    page_size: int = Query(10, ge=1, le=100),
    last_created_at: Optional[str] = Query(None),
    last_id: Optional[str] = Query(None)
):
    """Get posts for players the user follows"""
    try:
        uid = token_data["uid"]
        user_data = await firebase_service.get_user(uid)
        players_following = user_data["players_following"]

        last_cursor = None
        if last_created_at and last_id:
            last_cursor = {
                'created_at': datetime.fromisoformat(last_created_at),
                'id': last_id
            }

        results = await firebase_service.get_player_posts(
            player_ids=players_following,
            page_size=page_size,
            last_cursor=last_cursor
        )

        next_page_cursor = None
        if results["next_page_cursor"]:
            next_page_cursor = {
                'created_at': results["next_page_cursor"]['created_at'].isoformat(),
                'id': results["next_page_cursor"]['id']
            }

        return PostsResponse(
            posts=results["data"],
            next_page_cursor=next_page_cursor,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search(
    query: str = Query(..., min_length=2,
                       description="Search query for players or teams"),
    limit: int = Query(default=10, le=50,
                       description="Maximum number of results"),
    threshold: int = Query(
        default=60, le=100, description="Minimum similarity score (0-100)")
):
    try:
        normalized_query = normalize_text(query)

        players = await firebase_service.get_searchable_players()
        teams = await firebase_service.get_searchable_teams()

        results = []

        player_matches = search_entities(
            players, normalized_query, "player", threshold)
        results.extend(player_matches)

        team_matches = search_entities(
            teams, normalized_query, "team", threshold)
        results.extend(team_matches)

        sorted_results = sorted(
            results, key=lambda x: x.score, reverse=True)[:limit]

        return {"results": sorted_results}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_match_score(query: str, target: str) -> int:
    query = str(query)
    target = str(target)

    ratio = fuzz.ratio(query, target)
    partial_ratio = fuzz.partial_ratio(query, target)
    token_sort_ratio = fuzz.token_sort_ratio(query, target)
    token_set_ratio = fuzz.token_set_ratio(query, target)

    return max([ratio, partial_ratio, token_sort_ratio, token_set_ratio])


def search_entities(entities: List[Dict], query: str, entity_type: str, threshold: int) -> List[SearchResult]:
    results = []

    for entity in entities:
        score = get_match_score(query, normalize_text(entity["name"]))

        if entity_type == "team" and "alternative_names" in entity:
            for alt_name in entity["alternative_names"]:
                if alt_name:
                    alt_score = get_match_score(
                        query, normalize_text(alt_name))
                    score = max(score, alt_score)

        if score >= threshold:
            results.append(
                SearchResult(
                    id=entity["id"],
                    name=entity["name"],
                    type=entity_type,
                    metadata=entity["metadata"],
                    score=score
                )
            )

    return results


def create_metadata(entity: Dict, entity_type: str) -> Dict:
    if entity_type == "player":
        return {
            "position": entity.get("position"),
            "team": entity.get("team_name"),
            "number": entity.get("number"),
            "image_url": entity.get("image_url"),
            "nationality": entity.get("nationality"),
            "age": entity.get("age")
        }
    else:
        return {
            "league": entity.get("league"),
            "country": entity.get("country"),
            "logo_url": entity.get("logo_url"),
            "stadium": entity.get("stadium"),
            "founded": entity.get("founded")
        }


@router.post("/translate")
async def translate_text(request: TranslationRequest):
    """
    Translate a single block of text to the target language.
    valid language inputs: en, es, ja
    """
    try:
        translated_text = translation_service.translate_text(
            request.content, request.target_language, request.source_language
        )
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Translation failed: {str(e)}"
        )


@router.post("/translate/dict")
async def translate_dict(request: TranslationDictRequest):
    """
    Translate specific fields in a dictionary to the target language.
    """
    try:
        translated_data = translation_service.translate_dict(
            request.data, request.target_language, request.fields_to_translate
        )
        return {"translated_data": translated_data}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Translation failed: {str(e)}"
        )


@router.post("/verify-token")
async def verify_token(request: Request):
    try:
        body = await request.json()
        token = body.get("idToken")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        decoded_token = auth.verify_id_token(token)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "emailVerified": decoded_token.get("email_verified", False)
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/protected")
async def protected_route(token_data: Annotated[dict, Depends(verify_firebase_token)]):
    return {
        "message": "This is a protected route",
        "user": {
            "uid": token_data.get("uid"),
            "email": token_data.get("email"),
        }
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    user_dict = user.dict()
    return await firebase_service.create_user(uid, user_dict)


@router.get("/users/me", response_model=UserResponse)
async def get_current_user(
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    return await firebase_service.get_user(uid)


@router.put("/users/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    update_data = user_update.dict(exclude_unset=True)
    return await firebase_service.update_user(uid, update_data)


@router.delete("/users/me")
async def delete_current_user(
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    return await firebase_service.delete_user(uid)


@router.post("/users/me/teams/{team_id}")
async def follow_team(
    team_id: str,
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    user_data = await firebase_service.get_user(uid)

    if team_id not in user_data["teams_following"]:
        teams = user_data["teams_following"]
        teams.append(team_id)
        return await firebase_service.update_user(uid, {"teams_following": teams})
    return user_data


@router.delete("/users/me/teams/{team_id}")
async def unfollow_team(
    team_id: str,
    token_data: dict = Depends(verify_firebase_token)
):
    """Unfollow a team"""
    uid = token_data["uid"]
    user_data = await firebase_service.get_user(uid)

    if team_id in user_data["teams_following"]:
        teams = user_data["teams_following"]
        teams.remove(team_id)
        return await firebase_service.update_user(uid, {"teams_following": teams})
    return user_data


@router.post("/users/me/players/{player_id}")
async def follow_player(
    player_id: str,
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    user_data = await firebase_service.get_user(uid)

    if player_id not in user_data["players_following"]:
        players = user_data["players_following"]
        players.append(player_id)
        return await firebase_service.update_user(uid, {"players_following": players})
    return user_data


@router.delete("/users/me/players/{player_id}")
async def unfollow_player(
    player_id: str,
    token_data: dict = Depends(verify_firebase_token)
):
    uid = token_data["uid"]
    user_data = await firebase_service.get_user(uid)

    if player_id in user_data["players_following"]:
        players = user_data["players_following"]
        players.remove(player_id)
        return await firebase_service.update_user(uid, {"players_following": players})
    return user_data

router.include_router(ml_router)


@router.get("/posts/search")
async def search_posts(query: str):
    return await firebase_service.search_posts(query)

@router.get("/players/{player_id}")
async def get_player_by_id(player_id: str):
    return await firebase_service.get_player_by_id(player_id)

@router.get("/players")
async def get_all_players():
    return await firebase_service.get_all_players()

@router.get("/teams/{team_id}")
async def get_team_by_id(team_id: str):
    return await firebase_service.get_team_by_id(team_id)

@router.get("/teams")
async def get_all_teams():
    return await firebase_service.get_all_teams()
