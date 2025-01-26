import json
from datetime import datetime
import requests
from google.cloud import firestore
from dotenv import load_dotenv

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

def find_event_by_timestamp(data, target_timestamp):
    """
    Finds and returns the event that matches the target timestamp.

    :param json_file_path: Path to the JSON file containing game data.
    :param target_timestamp: The timestamp to search for (ISO 8601 format).
    :return: The event dictionary if found, else None.
    """
    # Convert target timestamp to datetime object for comparison
    target_time = datetime.fromisoformat(target_timestamp.replace('Z', '+00:00'))

    # Navigate to the list of all plays/events
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
            if start_time <= target_time <= end_time:
                return play

    return None

def find_team_by_player_id(db, mlb_person_id):
    """
    Finds and returns the team information for a given MLB person ID.

    :param db: Firestore client instance.
    :param mlb_person_id: The MLB person ID of the player.
    :return: A dictionary containing team information if found, else None.
    """
    try:
        players_ref = db.collection('players')
        query = players_ref.where('mlb_person_id', '==', mlb_person_id).stream()
        
        for player in query:
            player_data = player.to_dict()
            team_id = player_data.get('team_id')
            team_mlb_id = player_data.get('team_mlb_id')
            
            if team_id and team_mlb_id:
                teams_ref = db.collection('teams')
                team_query = teams_ref.where('mlb_id', '==', team_mlb_id).stream()
                
                for team in team_query:
                    return team.to_dict()
        
        print("Team not found for the given player ID.")
        return None
    except Exception as e:
        print(f"Error finding team: {str(e)}")
        return None

def get_game_info(game_pk, db):
    game_pk = 748266
    game_feed_url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    game_info = json.loads(requests.get(game_feed_url, timeout=200).content)
    with open("game_info_for_find_event.json", "w+") as f:
        json.dump(game_info, f)
    timestamp_to_find = '2024-02-22T20:15:09.578Z'
    
    event = find_event_by_timestamp(game_info, timestamp_to_find)

    with open("event_found.json", "w+") as f:
        json.dump(event, f)

    eventType = event.get('result', {}).get('eventType')
    player_role = EVENT_TO_PLAYER_ROLE.get(eventType)
    player_id = event.get('matchup', {}).get(player_role, {}).get('id')
    player_info = requests.get(f'https://statsapi.mlb.com/api/v1/people/{player_id}').content
    player_info = json.loads(player_info)
    with open("player_info.json", "w+") as f:
        json.dump(player_info, f)

    team = find_team_by_player_id(db, player_id)
    print(team)
    return event, team

# Example usage
if __name__ == "__main__":
    db = None
    try:
        load_dotenv()
        db = firestore.Client()
    except Exception as e:
        print(f"Error loading Firestore client: {str(e)}")
    if db:  
        event, team = get_game_info(748266, db)
    else:
        print("No Firestore client found")
    
    