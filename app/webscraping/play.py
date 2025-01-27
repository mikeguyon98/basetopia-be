from datetime import datetime
import requests
import json
import pytz
from dateutil import parser

def find_play_by_timestamp(game_pk, timestamp_str):
    """
    Find play information from a game given a timestamp.
    
    Args:
        game_pk (str): The game ID
        timestamp_str (str): ISO format timestamp (e.g. '2024-02-22T20:51:26.556Z')
    
    Returns:
        dict: Play information or None if not found
    """
    # Convert input timestamp to datetime object in UTC
    target_time = parser.parse(timestamp_str)
    if target_time.tzinfo is None:
        target_time = pytz.utc.localize(target_time)
    
    # Fetch game data
    try:
        url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
        response = requests.get(url)
        response.raise_for_status()
        game_data = response.json()
        with open(f"game_data_{game_pk}.json", "w") as f:
            json.dump(game_data, f)
        
        # Get all plays
        all_plays = game_data['liveData']['plays']['allPlays']
        
        # Find the play closest to the target time
        closest_play = None
        smallest_time_diff = None
        
        for play in all_plays:
            play_time_str = play['about']['endTime']
            if not play_time_str:
                continue
                
            play_time = parser.parse(play_time_str)
            time_diff = abs((play_time - target_time).total_seconds())
            
            if smallest_time_diff is None or time_diff < smallest_time_diff:
                smallest_time_diff = time_diff
                closest_play = play
        
        if closest_play:
            # Format relevant play information
            result = {
                'description': closest_play['result']['description'],
                'play_time': closest_play['about']['endTime'],
                'inning': f"{'Top' if closest_play['about']['isTopInning'] else 'Bottom'} {closest_play['about']['inning']}",
                'time_difference_seconds': smallest_time_diff,
                'play_id': closest_play['playEvents'][-1].get('playId') if closest_play['playEvents'] else None
            }
            return result
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game data: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Example usage:
# game_pk = "747066"  # Example game ID
# timestamp = "2024-02-22T20:51:26.556Z"  # Example timestamp

# result = find_play_by_timestamp(game_pk, timestamp)
# if result:
#     print("\nFound closest play:")
#     print(f"Description: {result['description']}")
#     print(f"Play Time: {result['play_time']}")
#     print(f"Inning: {result['inning']}")
#     print(f"Time Difference: {result['time_difference_seconds']:.2f} seconds")
#     if result['play_id']:
#         print(f"MLB Film Room Link: https://www.mlb.com/video/search?q=playid=\"{result['play_id']}\"")
# else:
#     print("No play found")

if __name__ == "__main__":
    game_pk = 748266  # Example game ID
    timestamp = "2024-02-22T21:46:59.042Z"  # Example timestamp

    result = find_play_by_timestamp(game_pk, timestamp)
    print(result)