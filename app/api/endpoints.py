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
from app.ml.endpoints import router as ml_router 
cloud_id = os.getenv("FIREBASE_PROJECT_ID", "basetopia-b9302")

router = APIRouter()
security = HTTPBearer()
translation_service = VertexAITranslation(project_id=cloud_id)
firebase_service = FirebaseService()


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