import json
from datetime import datetime, timedelta
import requests
from google.cloud import firestore
from dotenv import load_dotenv
from highlights import get_highlights
from players import process_player_data
import pandas as pd
import os

# Configuration for Vertex AI Search
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')  # Ensure this is set in your .env file or environment
LOCATION = os.getenv('VERTEX_AI_LOCATION', 'us-central1')  # Default location or set in .env
DATA_STORE_ID = os.getenv('VERTEX_AI_DATA_STORE_ID')  # Set this in your .env file or environment

EVENT_TO_PLAYER_ROLE = {
    'walk': 'batter',
    'hit': 'batter',
    'single': 'batter',
    'double': 'batter',
    'triple': 'batter',
    'home_run': 'batter',
    'run': 'batter',
    'strikeout': 'batter',
    'ground_out': 'batter',
    'fly_out': 'batter',
    'hit_by_pitch': 'batter',
    'strike': 'pitcher',
    'pitch': 'pitcher',
    'walk_issued': 'pitcher',
    'error': 'pitcher',
    'assist': 'pitcher',
    'put_out': 'pitcher',
    'field_out': 'pitcher',
}

def process_endpoint_url(url, key):
    """
    Fetches JSON data from the specified URL and extracts the value associated with the given key.

    Args:
        url (str): The API endpoint URL.
        key (str): The key to extract from the JSON response.

    Returns:
        The value associated with the specified key, or None if an error occurs.
    """
    try:
        response = requests.get(url, timeout=200)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        return data.get(key, None)
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def get_all_games_from_season(season):
    """
    Retrieves all MLB games for a given season and returns both a DataFrame of games and a list of gameIds.

    Args:
        season (int): The MLB season year (e.g., 2024).

    Returns:
        tuple:
            - pd.DataFrame: A DataFrame containing all games for the specified season.
            - list: A list of gameIds (gamePk) for the specified season.
    """
    schedule_endpoint_url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={season}'
    schedule_dates = process_endpoint_url(schedule_endpoint_url, "dates")

    if schedule_dates is None:
        print(f"Failed to retrieve schedule for season {season}.")
        return None, None

    try:
        # Convert the list of dates to a DataFrame
        dates_df = pd.DataFrame(schedule_dates)

        # Check if 'games' column exists
        if 'games' not in dates_df.columns:
            print("No 'games' key found in the schedule data.")
            return None, None

        # Explode the 'games' column to have one game per row
        games_exploded = dates_df.explode('games').reset_index(drop=True)

        # Drop rows where 'games' is NaN (if any)
        games_exploded = games_exploded.dropna(subset=['games'])

        # Normalize the 'games' column to flatten the JSON structure
        games = pd.json_normalize(games_exploded['games'])

        # Extract the list of game IDs
        game_ids = games['gamePk'].tolist()

        return games, game_ids
    except KeyError as e:
        print(f"Error processing games data: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

def find_event_by_timestamp(data, target_timestamp):
    """
    Finds and returns the event that matches the target timestamp.

    :param json_file_path: Path to the JSON file containing game data.
    :param target_timestamp: The timestamp to search for (ISO 8601 format).
    :return: The event dictionary if found, else None.
    """
    # Convert target timestamp to datetime object for comparison
    target_time = datetime.fromisoformat(target_timestamp.replace('Z', '+00:00'))

    all_plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])

    for play in all_plays:
        about = play.get('about', {})
        start_timestamp = about.get('startTime')
        end_timestamp = about.get('endTime')  # Assuming 'endTime' exists

        if start_timestamp and end_timestamp:
            # Convert start and end timestamps to datetime objects
            start_time = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))

            # Check if target_time is within the interval [start_time, end_time]
            buffer = timedelta(seconds=1)  # Add a 1-second buffer
            if (start_time - buffer) <= target_time <= (end_time + buffer):
                return play

    return None

def find_team_by_player_id(db, mlb_person_id):
    """
    Finds and returns the team information for a given MLB person ID.
    If the player is not found in Firestore, fetches from MLB API and stores it.

    :param db: Firestore client instance.
    :param mlb_person_id: The MLB person ID of the player.
    :return: A dictionary containing team information if found, else None.
    """
    try:
        # First, try to find the player in Firestore
        players_ref = db.collection('players')
        query = players_ref.where('mlb_person_id', '==', mlb_person_id).stream()

        player_data = None
        for player in query:
            player_data = player.to_dict()
            break  # We only need the first match

        # If player not found, fetch from MLB API and store
        if not player_data:
            print(f"Player {mlb_person_id} not found in Firestore. Fetching from MLB API...")
            player_url = f'https://statsapi.mlb.com/api/v1/people/{mlb_person_id}?fields=id,fullName,currentTeam'
            response = requests.get(player_url, timeout=10)
            response.raise_for_status()
            
            mlb_data = response.json()
            print(f"MLB API Response: {mlb_data}")  # Debug print
            
            if not mlb_data.get('people'):
                print(f"No player data returned from MLB API for ID: {mlb_person_id}")
                return None
                
            mlb_player_data = mlb_data['people'][0]

            if mlb_player_data and 'currentTeam' in mlb_player_data:
                team_mlb_id = mlb_player_data['currentTeam']['id']

                # Find team in Firestore by MLB ID
                teams_ref = db.collection('teams')
                team_query = teams_ref.where('mlb_id', '==', team_mlb_id).stream()
                team_data = None
                for team in team_query:
                    team_data = team.to_dict()
                    break

                if team_data:
                    # Create a player dictionary compatible with process_player_data
                    player_data = requests.get(f'https://statsapi.mlb.com/api/v1/people/{mlb_person_id}', timeout=10)
                    player_dict = player_data.json()

                    # Process the player data
                    new_player = process_player_data(player_dict, team_data['id'], team_mlb_id)

                    # Save the processed player to Firestore
                    players_ref.document(new_player['id']).set(new_player)
                    print("Added Player")
                    return team_data
                else:
                    print(f"Team not found in Firestore for MLB ID: {team_mlb_id}")

        # If we found the player in Firestore, get their team
        if player_data and player_data.get('team_mlb_id'):
            teams_ref = db.collection('teams')
            team_query = teams_ref.where('mlb_id', '==', player_data['team_mlb_id']).stream()

            for team in team_query:
                return team.to_dict()

        print("Team not found for the given player ID.")
        return None
    except Exception as e:
        print(f"Error finding team: {str(e)}")
        print(f"Full error details: ", e.__class__.__name__)
        import traceback
        traceback.print_exc()
        return None

def get_game_info(game_pk, db, timestamp_to_find):
    """
    Retrieves event and team information for a specific game and timestamp.

    :param game_pk: The unique identifier for the game.
    :param db: Firestore client instance.
    :param timestamp_to_find: The timestamp to search for in ISO 8601 format.
    :return: Tuple containing the event and team information.
    """
    game_feed_url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    try:
        response = requests.get(game_feed_url, timeout=200)
        response.raise_for_status()
        game_info = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch game info for game {game_pk}: {e}")
        return None, None

    event = find_event_by_timestamp(game_info, timestamp_to_find)
    if not event:
        print(f"No event found at timestamp {timestamp_to_find} in game {game_pk}.")
        return None, None

    eventType = event.get('result', {}).get('eventType')
    player_role = EVENT_TO_PLAYER_ROLE.get(eventType)
    player_id = event.get('matchup', {}).get(player_role, {}).get('id')

    if not player_id:
        print(f"No player ID found for event at timestamp {timestamp_to_find} in game {game_pk}.")
        return event, None

    try:
        player_response = requests.get(f'https://statsapi.mlb.com/api/v1/people/{player_id}', timeout=200)
        player_response.raise_for_status()
        player_info = player_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch player info for player {player_id}: {e}")
        return event, None

    team = find_team_by_player_id(db, player_id)
    print(team)
    return event, team

def save_json(data, file_path):
    """
    Saves the given data to a JSON file.

    Args:
        data: The data to save.
        file_path (str): The path to the JSON file.
    """
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            # Handle Firestore DatetimeWithNanoseconds
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return super().default(obj)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4, cls=CustomEncoder)

def load_json(file_path):
    """
    Loads and returns data from a JSON file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        The data loaded from the JSON file, or an empty list if the file does not exist.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def process_season_highlights(season):
    """
    Processes all games for a given season, retrieves highlights, finds specific highlights based on a timestamp,
    identifies the associated team, and uploads the compiled data to Vertex AI Search with checkpointing.

    Args:
        season (int): The MLB season year (e.g., 2024).
    """
    # Load environment variables and initialize Firestore client
    load_dotenv()
    try:
        db = firestore.Client()
    except Exception as e:
        print(f"Error loading Firestore client: {str(e)}")
        return

    # Get game IDs for the season
    games_df, game_ids = get_all_games_from_season(season)
    if not game_ids:
        print(f"No games found for season {season}.")
        return

    # Get processed games from Firestore
    processed_games_ref = db.collection('processed_games')
    processed_docs = processed_games_ref.where('season', '==', season).stream()
    processed_game_ids = {doc.get('game_id') for doc in processed_docs}

    # Initialize a list to hold documents for batch upload
    documents_to_upload = []

    # Process each game with checkpointing
    for game_id in game_ids:
        if str(game_id) in processed_game_ids:
            print(f"Skipping already processed game ID: {game_id}")
            continue

        print(f"Processing game ID: {game_id}")
        highlights = get_highlights(game_id)
        if not highlights:
            print(f"No highlights found for game ID: {game_id}")
            # Mark as processed even if no highlights
            processed_games_ref.add({
                'game_id': str(game_id),
                'season': season,
                'processed_at': firestore.SERVER_TIMESTAMP
            })
            continue

        print(f"Found {len(highlights)} highlight(s) for game {game_id}:\n")
        for highlight in highlights:
            highlight_timestamp = highlight.get("date")
            if not highlight_timestamp:
                continue

            event, team = get_game_info(game_id, db, highlight_timestamp)
            if not event:
                # Store highlight with team set to None
                compiled_data = {
                    "game_id": str(game_id),
                    "highlight": highlight,
                    "team": None,
                    "created_at": firestore.SERVER_TIMESTAMP
                }
                documents_to_upload.append(compiled_data)
                continue

            compiled_data = {
                "game_id": str(game_id),
                "highlight": highlight,
                "team": team,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            documents_to_upload.append(compiled_data)

        # Upload documents in batches
        BATCH_SIZE = 100
        highlights_ref = db.collection('highlights')
        while len(documents_to_upload) >= BATCH_SIZE:
            batch = db.batch()
            for doc in documents_to_upload[:BATCH_SIZE]:
                doc_ref = highlights_ref.document()
                batch.set(doc_ref, doc)
            batch.commit()
            documents_to_upload = documents_to_upload[BATCH_SIZE:]

        # Mark game as processed
        processed_games_ref.add({
            'game_id': str(game_id),
            'season': season,
            'processed_at': firestore.SERVER_TIMESTAMP
        })
        print(f"Checkpoint updated for game ID: {game_id}")

    # Upload any remaining documents
    if documents_to_upload:
        batch = db.batch()
        highlights_ref = db.collection('highlights')
        for doc in documents_to_upload:
            doc_ref = highlights_ref.document()
            batch.set(doc_ref, doc)
        batch.commit()

    print(f"All season highlights have been processed and saved to Firestore.")
    

def test_find_team():
    load_dotenv()
    db = firestore.Client()
    
    # Test with a known MLB player ID (e.g., Mike Trout's ID is 545361)
    test_player_id = 606192
    result = find_team_by_player_id(db, test_player_id)
    print(f"Result for player {test_player_id}:", result)

# Example usage
if __name__ == "__main__":
    SEASON_YEAR = 2024
    process_season_highlights(SEASON_YEAR)
