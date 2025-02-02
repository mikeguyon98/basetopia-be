from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Literal
from app.ml.agent import run_agent
from enum import Enum
from app.services.translator import VertexAITranslation
from app.services.firebase_service import FirebaseService
from app.ml.output_schema import AgentResponse
from datetime import datetime

router = APIRouter(
    prefix="/ml",
    tags=["AI Agent"],
    responses={404: {"description": "Not found"}},
)

class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    JAPANESE = "ja"

class AgentQueryRequest(BaseModel):
    user_query: str
    input_language: SupportedLanguage

class FinalResponse(BaseModel):
    en: AgentResponse
    es: AgentResponse
    ja: AgentResponse

class AgentQueryResponse(BaseModel):
    final_response: FinalResponse
    error: Optional[str] = None

class SaveHighlightRequest(BaseModel):
    highlight_data: FinalResponse

class SaveHighlightResponse(BaseModel):
    success: bool
    document_id: str
    message: str = "Highlight saved successfully"

class NextPageCursor(BaseModel):
    created_at: str
    id: str

class PaginatedHighlightsResponse(BaseModel):
    posts: List[AgentResponse]
    next_page_cursor: Optional[NextPageCursor]
    page_size: int

firebase_service = FirebaseService()

@router.post("/agent/query", response_model=AgentQueryResponse)
async def query_agent(request: AgentQueryRequest):
    """
    Submit a query to the AI agent and get a response.
    """
    try:
        # Run the agent to get the English response
        response_en = run_agent(request.user_query)
        
        # Initialize the translation service
        translator = VertexAITranslation()
        
        # Define target languages
        target_languages = ["es", "ja"]
        
        # Initialize the final_response with English
        final_response = {"en": response_en}
        
        # List of fields to translate
        TRANSLATABLE_FIELDS = {"title", "description", "content"}
        
        # Function to recursively translate specified fields in the dictionary
        def translate_recursive(data: dict, translator_instance: VertexAITranslation, target_lang: str) -> dict:
            translated_data = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    translated_data[key] = translate_recursive(value, translator_instance, target_lang)
                elif isinstance(value, list):
                    translated_list = []
                    for item in value:
                        if isinstance(item, dict):
                            translated_list.append(translate_recursive(item, translator_instance, target_lang))
                        else:
                            # Handle non-dict items if necessary
                            translated_list.append(item)
                    translated_data[key] = translated_list
                elif key in TRANSLATABLE_FIELDS and isinstance(value, str):
                    translated_text = translator_instance.translate_text(value, target_lang)
                    translated_data[key] = translated_text
                else:
                    translated_data[key] = value
            return translated_data
        
        # Translate the response into each target language
        for lang in target_languages:
            translated_response = translate_recursive(response_en, translator, lang)
            final_response[lang] = translated_response
        
        return AgentQueryResponse(final_response=FinalResponse(**final_response))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/posts", response_model=SaveHighlightResponse, status_code=201)
async def post_highlight(request: SaveHighlightRequest):
    """
    Post a highlight to Firebase.
    """
    try:
        doc_id = await firebase_service.save_highlight_post(request.highlight_data.dict())
        return SaveHighlightResponse(success=True, document_id=doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/posts", response_model=PaginatedHighlightsResponse)
async def get_highlight_posts(
    page_size: int = Query(10, ge=1, le=100),
    last_created_at: Optional[str] = Query(None),
    last_id: Optional[str] = Query(None)
):
    """
    Retrieve paginated highlight posts from Firebase using cursor-based pagination.
    """
    try:
        # Prepare the last_cursor if both last_created_at and last_id are provided
        if last_created_at and last_id:
            last_created_at_parsed = datetime.fromisoformat(last_created_at)
            last_cursor = {
                'created_at': last_created_at_parsed,
                'id': last_id
            }
        else:
            last_cursor = None

        results = await firebase_service.get_paginated_highlights(page_size, last_cursor)
        
        # Prepare next_page_cursor for response
        if results["next_page_cursor"]:
            next_page_cursor = {
                'created_at': results["next_page_cursor"]['created_at'].isoformat(),
                'id': results["next_page_cursor"]['id']
            }
        else:
            next_page_cursor = None

        return PaginatedHighlightsResponse(
            posts=results["data"],
            next_page_cursor=next_page_cursor,
            page_size=page_size,
            total_items=len(results["data"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))