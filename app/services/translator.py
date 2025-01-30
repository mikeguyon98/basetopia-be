import os
from typing import List, Optional
from google.cloud import translate_v3beta1 as translate
from google.oauth2 import service_account


class VertexAITranslation:
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "global",
        credentials_path: Optional[str] = None
    ):
        # Determine project ID
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError(
                "No project ID provided. Set GOOGLE_CLOUD_PROJECT env var.")

        # Determine credentials path
        credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS')

        # Load credentials
        try:
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.client = translate.TranslationServiceClient(
                    credentials=credentials)
            else:
                # Fallback to default credentials
                self.client = translate.TranslationServiceClient()
        except Exception as e:
            print(f"Credentials loading failed: {e}")
            raise

        self.location = location
        self.parent = f"projects/{self.project_id}/locations/{self.location}"

    def _validate_input(self, text: str, target_language: str):
        """Validate translation inputs"""
        if not text:
            raise ValueError("Text cannot be empty")
        if not target_language:
            raise ValueError("Target language must be specified")

    def _split_text(self, text: str, max_chars: int = 30000) -> List[str]:
        """Split long text into chunks"""
        chunks = []
        while len(text) > max_chars:
            split_idx = text[:max_chars].rfind(" ")
            if split_idx == -1:
                split_idx = max_chars
            chunks.append(text[:split_idx])
            text = text[split_idx:].strip()
        chunks.append(text)
        return chunks

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text with error handling and chunk support"""
        self._validate_input(text, target_language)

        text_chunks = self._split_text(text)
        translated_chunks = []

        for chunk in text_chunks:
            try:
                response = self.client.translate_text(
                    request={
                        "parent": self.parent,
                        "contents": [chunk],
                        "target_language_code": target_language,
                        "mime_type": "text/plain",
                    }
                )
                translated_chunks.append(
                    response.translations[0].translated_text)
            except Exception as e:
                print(f"Translation chunk error: {e}")
                raise

        return " ".join(translated_chunks)

    def translate_dict(
        self,
        data: dict,
        target_language: str,
        fields_to_translate: List[str]
    ) -> dict:
        """Translate specific dictionary fields"""
        for field in fields_to_translate:
            if field in data and data[field]:
                data[field] = self.translate_text(
                    str(data[field]), target_language)
        return data
