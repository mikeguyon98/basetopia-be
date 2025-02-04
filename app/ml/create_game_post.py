from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.webscraping.game import get_game_summary
from app.webscraping.highlights import get_highlights
from app.ml.output_schema import AgentResponse
from dotenv import load_dotenv
import requests
import datetime

def get_last_100_game_ids():
    """
    Fetches the last 100 MLB game IDs (gamePk) from the MLB Stats API.

    The function dynamically increases the date range until at least 100 games are found.
    It calls the schedule endpoint with startDate and endDate, then extracts, sorts, and returns
    the game IDs of the most recent games.

    Returns:
        List[int]: A list of the last 100 game IDs sorted by gameDate descending.
    """
    days_window = 300  # start with a 30-day window
    while True:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days_window)
        # Format dates as YYYY-MM-DD
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        schedule_url = (
            f"https://statsapi.mlb.com/api/v1/schedule?"
            f"sportId=1&startDate={start_date_str}&endDate={end_date_str}"
        )
        try:
            response = requests.get(schedule_url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching schedule data: {e}")
            return []
        
        games = []
        # The response contains a list of dates and, for each date, a list of games.
        for date_entry in data.get("dates", []):
            games.extend(date_entry.get("games", []))
        
        # Sort games by their 'gameDate' in descending order (most recent first).
        games_sorted = sorted(games, key=lambda x: x.get("gameDate", ""), reverse=True)
        
        if len(games_sorted) >= 100:
            # Return the gamePk for the most recent 100 games.
            return [game.get("gamePk") for game in games_sorted[:100]]
        else:
            # Not enough games found in the current window; increase the window and try again.
            days_window += 15
            if days_window > 120:
                print(f"Not enough games found even after checking the past {days_window} days.")
                return [game.get("gamePk") for game in games_sorted]

def create_game_post(game_id: int):
    """
    Generates game posts for the given game ID by fetching the game summary and highlights,
    then using an LLM (via LangChain and OpenAI) to produce a post with guaranteed structured output.
    
    The generated JSON includes:
      - title: A summary title for the response.
      - highlights: A list containing dictionaries with a video URL and descriptive narrative.
      - content: A detailed Markdown formatted post.
      - team_tags: A list of the teams' shortName values (passed in from the game summary).
      - player_tags: An empty list.
      
    After obtaining the post in English, the function translates the post into Spanish and Japanese.
    
    Returns:
        dict: A dictionary with keys "en", "es", and "ja" for each localized version.
    """
    # Fetch the game summary and highlights from our webscraping modules.
    game_summary = get_game_summary(game_id)
    highlights = get_highlights(game_id)
    if not highlights:
        print("No highlights found for this game.")
        return {}

    # Extract team short names from game_summary.
    # (Assuming game_summary contains a "teams" key with "home" and "away" dictionaries)
    team_tags = []
    teams_info = game_summary.get("teams", {})
    if "Away Team" in teams_info:
       team_tags.append(teams_info["Away Team"])
    if "Home Team" in teams_info:
        team_tags.append(teams_info["Home Team"])

    # Convert the game summary dictionary into a human-readable string.
    game_summary_str = "\n".join([f"{key}: {value}" for key, value in game_summary.items()])

    # Define an updated prompt template that includes the team_tags and extended output keys.
    prompt_template = PromptTemplate(
        input_variables=["game_summary", "highlights"],
        template="""
You are a professional sports journalist. Below is a game summary, team details, and specific game highlights detail.
Use this context to create an engaging post for a sports website.

Game Summary:
{game_summary}

Highlights:
{highlights}

Include every highlight passed in the post. Make sure to include the video URL and description for each highlight.
Additionally, incorporate the game summary and team details into the content section. Format the content as Markdown and tell a compelling story.

Return your answer strictly as valid JSON with the following structure:
{{
    "title": "<string>",
    "highlights": [{{"video_url": "<string>", "description": "<string>"}}],
    "content": "<string>",
}}
Ensure that the JSON is properly formatted.
"""
    )

    # Initialize ChatOpenAI and configure it for structured JSON output.
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    structured_llm = llm.with_structured_output(AgentResponse, method="json_mode")
    # Chain the prompt template with the LLM.
    chain = prompt_template | structured_llm

    prompt_dict = {
        "game_summary": game_summary_str,
        "highlights": highlights,
    }

    try:
        english_post = chain.invoke(input=prompt_dict)
    except Exception as e:
        print(f"Error processing highlights: {e}")
        return {}

    # <--- Convert to dict before translation --->
    english_post = english_post.dict()

    # Import and initialize the translator.
    from app.services.translator import VertexAITranslation
    translator = VertexAITranslation()

    # Specify which fields should be translated (including nested "description" within highlights).
    TRANSLATABLE_FIELDS = {"title", "content", "description"}

    def translate_recursive(data: dict, target_lang: str) -> dict:
        """
        Recursively translates string fields in the dictionary that are listed in TRANSLATABLE_FIELDS.
        """
        translated_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                translated_data[key] = translate_recursive(value, target_lang)
            elif isinstance(value, list):
                translated_list = []
                for item in value:
                    if isinstance(item, dict):
                        translated_list.append(translate_recursive(item, target_lang))
                    else:
                        translated_list.append(item)
                translated_data[key] = translated_list
            elif key in TRANSLATABLE_FIELDS and isinstance(value, str):
                translated_text = translator.translate_text(value, target_lang)
                translated_data[key] = translated_text
            else:
                translated_data[key] = value
        return translated_data

    spanish_post = translate_recursive(english_post, "es")
    japanese_post = translate_recursive(english_post, "ja")

    final_response = {
        "en": english_post,
        "es": spanish_post,
        "ja": japanese_post,
    }
    final_response["team_tags"] = team_tags
    final_response["player_tags"] = []
    return final_response

if __name__ == "__main__":
    load_dotenv()
    #get last 100 game_ids
    # game_ids = get_last_100_game_ids()
    # for game_id in game_ids:
    #     posts = create_game_post(game_id)

    response = create_game_post(775302)
    print(response)
    
    
    # posts = create_game_post(example_game_id)
    # print(posts.model_dump())