from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated, Optional
from firebase_admin import auth
from fastapi import APIRouter, HTTPException, Query
from app.services.translator import VertexAITranslation
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
cloud_id = os.getenv("FIREBASE_PROJECT_ID", "basetopia-b9302")

router = APIRouter()
security = HTTPBearer()
translation_service = VertexAITranslation(project_id=cloud_id)


class TranslationRequest(BaseModel):
    content: str
    target_language: str


class TranslationDictRequest(BaseModel):
    data: dict
    target_language: str
    fields_to_translate: list


@router.post("/translate")
async def translate_text(request: TranslationRequest):
    """
    Translate a single block of text to the target language.
    """
    try:
        translated_text = translation_service.translate_text(
            request.content, request.target_language
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


@router.get("/user/profile")
async def get_user_profile(
    token_data: Annotated[dict, Depends(verify_firebase_token)],
    target_language: Optional[str] = None
):
    try:
        user = auth.get_user(token_data['uid'])
        response_data = {
            "uid": user.uid,
            "email": user.email,
            "displayName": user.display_name,
            "photoURL": user.photo_url,
            "emailVerified": user.email_verified
        }

        if target_language:
            # Translate relevant fields
            response_data = await translation_service.translate_dict(
                response_data,
                target_language,
                fields_to_translate=["displayName"]
            )

        return response_data
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
