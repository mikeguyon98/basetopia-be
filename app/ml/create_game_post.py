from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import PromptTemplate
from app.webscraping.game import get_game_summary
from app.webscraping.highlights import get_highlights
from app.ml.output_schema import AgentResponse
from dotenv import load_dotenv

def create_game_post(post_details: dict) -> AgentResponse:
    # Initialize the Vertex AI based chat model
    model = ChatVertexAI(model="chat-bison@001")  # Replace with your desired Vertex AI model

    # Define a prompt template for creating game posts
    prompt_template = PromptTemplate(
        input_variables=["summary", "highlights"],
        template="Game Summary: {summary}\nHighlights: {highlights}"
    )

    # Generate a game summary and highlights
    summary = get_game_summary(post_details.get("game_id"))
    highlights = get_highlights(post_details.get("game_id"))

    prompt = prompt_template.format(summary=summary, highlights=highlights)

    # Generate the final post content using Vertex AI
    response = model.generate(prompt)
    # Parse and return the response according to the AgentResponse schema
    return AgentResponse.parse_raw(response)

if __name__ == "__main__":
    load_dotenv()
    # Example: use a game ID (adjust as necessary)
    example_game_id = 748266
    posts = create_game_post({"game_id": example_game_id})
    print(posts.model_dump())