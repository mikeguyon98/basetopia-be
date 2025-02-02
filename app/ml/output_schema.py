from pydantic import BaseModel, Field
from typing import List

class Highlight(BaseModel):
    video_url: str = Field(..., description="URL of the highlight video")
    description: str = Field(..., description="Description of the highlight")

class ContentItem(BaseModel):
    subtitle: str = Field(..., description="Subtitle for the content section")
    content: str = Field(..., description="Content text")

class AgentResponse(BaseModel):
    title: str = Field(..., description="A title summarizing the response")
    highlights: List[Highlight] = Field(
        default_factory=list,
        description="List of highlights, each with a video URL and description"
    )
    content: str = Field(..., description="Content text in Markdown format")