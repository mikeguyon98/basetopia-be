from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.ml.agent import run_agent
from enum import Enum
from app.services.translator import VertexAITranslation

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

class AgentQueryResponse(BaseModel):
    final_response: dict
    error: Optional[str] = None

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
        
        # Function to recursively translate the dictionary
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
                            # If the list contains non-dict items, handle accordingly
                            if isinstance(item, str):
                                translated_text = translator_instance.translate_text(item, target_lang)
                                translated_list.append(translated_text)
                            else:
                                translated_list.append(item)
                    translated_data[key] = translated_list
                elif isinstance(value, str):
                    translated_data[key] = translator_instance.translate_text(value, target_lang)
                else:
                    translated_data[key] = value
            return translated_data
        
        # Translate the response into each target language
        for lang in target_languages:
            translated_response = translate_recursive(response_en, translator, lang)
            final_response[lang] = translated_response
        
        return AgentQueryResponse(final_response=final_response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))