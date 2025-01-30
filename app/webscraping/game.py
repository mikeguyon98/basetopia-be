import json
import requests


def get_game_summary(game_pk):
    """
    Gets a summary of key information for a specific game, including top performers.

    Args:
        game_pk: The unique identifier for the game

    Returns:
        Dictionary containing game summary information
    """
    # Get game feed data
    game_feed_url = f'https://statsapi.mlb.com/api/v1.1/game/{
        game_pk}/feed/live'
    game_info = json.loads(requests.get(game_feed_url).content)

    # Extract key information
    game_data = game_info['gameData']
    live_data = game_info['liveData']

    # Build summary dictionary
    summary = {
        'Date': game_data['datetime']['officialDate'],
        'Status': game_data['status']['detailedState'],
        'Venue': game_data['venue']['name'],
        'Away Team': game_data['teams']['away']['name'],
        'Home Team': game_data['teams']['home']['name'],
        'Away Score': live_data['linescore']['teams']['away']['runs'],
        'Home Score': live_data['linescore']['teams']['home']['runs'],
        'Winning Pitcher': None,
        'Losing Pitcher': None,
        'Save': None,
        'Top Performers': []
    }

    # Add pitcher decisions if game is complete
    if game_data['status']['statusCode'] in ('F', 'FT', 'FR'):
        decisions = live_data['decisions']
        if 'winner' in decisions:
            summary['Winning Pitcher'] = decisions['winner']['fullName']
        if 'loser' in decisions:
            summary['Losing Pitcher'] = decisions['loser']['fullName']
        if 'save' in decisions:
            summary['Save'] = decisions['save']['fullName']

    # Add top performers
    if 'topPerformers' in live_data['boxscore']:
        for performer in live_data['boxscore']['topPerformers']:
            player = performer['player']
            stats = player['stats'].get(
                'batting', {}) or player['stats'].get('pitching', {})

            # Create performer summary
            perf_summary = {
                'Name': player['person']['fullName'],
                'Position': player['position']['name'],
                'Stats': stats.get('summary', 'No stats available'),
                'Type': performer['type'],
                'Game Score': performer.get('gameScore', 'N/A')
            }
            summary['Top Performers'].append(perf_summary)

    return summary

# # Example usage:
# game_pk = 748266  # You can change this to any game ID
# summary = get_game_summary(game_pk)

# # Print summary in a formatted way
# for key, value in summary.items():
#     if key != 'Top Performers':
#         print(f"{key}: {value}")
#     else:
#         print("\nTop Performers:")
#         for performer in value:
#             print(f"\n  {performer['Name']} ({performer['Position']}):")
#             print(f"  - Performance: {performer['Stats']}")
#             print(f"  - Type: {performer['Type']}")
#             print(f"  - Game Score: {performer['Game Score']}")


if __name__ == "__main__":
    game_pk = 748266
    summary = get_game_summary(game_pk)
    for key, value in summary.items():
        print(f"{key}: {value}")
