from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.webscraping.game import get_game_summary
from app.webscraping.highlights import get_highlights
from app.ml.output_schema import AgentResponse
from dotenv import load_dotenv

def create_game_post(game_id: int):
    """
    Generates game posts for the given game ID by fetching the game summary and highlights,
    then using an LLM (via LangChain and OpenAI) to produce a post for each highlight with 
    guaranteed structured output.

    Each post is returned in the format defined by the AgentResponse output schema:
      - title: A summary title for the response.
      - highlights: A list containing dictionaries with a video URL and a descriptive narrative.
      - content: A detailed Markdown formatted post.

    Args:
        game_id (int): The unique identifier for the game.

    Returns:
        List[AgentResponse]: A list of posts (one per highlight) generated using the LLM.
    """
    # Fetch the game summary and highlights from our webscraping modules.
    game_summary = get_game_summary(game_id)
    highlights = get_highlights(game_id)
    if not highlights:
        print("No highlights found for this game.")
        return []

    # Define a prompt template for the LLM.
    prompt_template = PromptTemplate(
        input_variables=["game_summary", "highlight_title", "date", "video_url", "image_url"],
        template="""
You are a professional sports journalist. Below is a game summary and a specific game highlight detail.
Use this context to create an engaging post for a sports website.

Game Summary:
{game_summary}

highlights:
{highlights}

Please include every highlight passed in the post. Make sure to include the video URL and description for each highlight. Additionally please include the game summary in the content section. Format the content as markdown and tell a compelling story.

Return your answer strictly as valid JSON with the following structure:
{{
    "title": "<string>",
    "highlights": [{{"video_url": "<string>", "description": "<string>"}}],
    "content": "<string>"
}}
Ensure that the JSON is properly formatted.
"""
    )

    # Initialize ChatOpenAI and configure it for structured JSON output.
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    # Use JSON mode to guarantee the output conforms to AgentResponse.
    structured_llm = llm.with_structured_output(AgentResponse, method="json_mode")
    
    # --- FIXED CHAIN COMPOSITION ---
    # The prompt template should come first so it can format inputs.
    # Then, its output (a string) is passed to the LLM.
    chain = prompt_template | structured_llm

    # Convert the game summary dictionary into a human-readable string.
    game_summary_str = "\n".join([f"{key}: {value}" for key, value in game_summary.items()])

    # Iterate over each highlight and generate a post.
    try:
        # Instead of manual formatting, pass the kwargs so that the chain uses the prompt_template
        print("HIGHLIGHTS: ", highlights)
        print("Highlights length: ", len(highlights))
        prompt_dict = {
            "game_summary": game_summary_str,
            "highlights": highlights
        }
        agent_post = chain.invoke(input=prompt_dict)
    except Exception as e:
        print(f"Error processing highlights: {e}")

    return agent_post

if __name__ == "__main__":
    load_dotenv()
    # Example: use a game ID (adjust as necessary)
    example_game_id = 748266
    posts = create_game_post(example_game_id)
    print(posts.model_dump())