from google.cloud import firestore
import requests
import json
from datetime import datetime
import uuid
from dotenv import load_dotenv

def initialize_firestore():
    """Initialize and return Firestore client."""
    return firestore.Client()

def fetch_team_roster(team_mlb_id):
    """Fetch roster data for a specific team from MLB API."""
    roster_url = f'https://statsapi.mlb.com/api/v1/teams/{team_mlb_id}/roster?season=2025'
    response = requests.get(roster_url, timeout=10)
    data = json.loads(response.content)
    return data.get('roster', [])

def process_player_data(player, team_id, team_mlb_id):
    """Process raw player data into desired format."""
    # Generate unique ID and timestamp
    player_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    # Map and prefix fields
    processed_data = {
        'id': player_id,
        'created_at': created_at,
        'team_id': team_id,  # Reference to our team document
        'team_mlb_id': team_mlb_id,
        'mlb_jerseyNumber': player.get('jerseyNumber'),
        'mlb_parentTeamId': player.get('parentTeamId'),
        'mlb_person_id': player.get('person', {}).get('id'),
        'mlb_person_fullName': player.get('person', {}).get('fullName'),
        'mlb_person_link': player.get('person', {}).get('link'),
        'mlb_position_code': player.get('position', {}).get('code'),
        'mlb_position_name': player.get('position', {}).get('name'),
        'mlb_position_type': player.get('position', {}).get('type'),
        'mlb_position_abbreviation': player.get('position', {}).get('abbreviation'),
        'mlb_status_code': player.get('status', {}).get('code'),
        'mlb_status_description': player.get('status', {}).get('description')
    }
    
    return processed_data

def save_players_to_firestore(db, players_data):
    """Save processed player data to Firestore."""
    batch = db.batch()
    players_ref = db.collection('players')
    
    for player in players_data:
        doc_ref = players_ref.document(player['id'])
        batch.set(doc_ref, player)
    
    batch.commit()
    return len(players_data)

def get_all_teams(db):
    """Retrieve all teams from Firestore."""
    teams_ref = db.collection('teams')
    return teams_ref.stream()

def main():
    """Main function to orchestrate the player data pipeline."""
    try:
        # Initialize Firestore
        load_dotenv()
        db = initialize_firestore()
        
        # Get all teams from Firestore
        teams = get_all_teams(db)
        total_players = 0
        
        # For each team, fetch and save roster
        for team in teams:
            team_data = team.to_dict()
            team_mlb_id = team_data['mlb_id']
            team_id = team_data['id']
            
            # Fetch roster data
            roster_data = fetch_team_roster(team_mlb_id)
            
            # Process each player
            processed_players = [
                process_player_data(player, team_id, team_mlb_id)
                for player in roster_data
            ]
            
            # Save to Firestore
            if processed_players:
                saved_count = save_players_to_firestore(db, processed_players)
                total_players += saved_count
                print(f"Saved {saved_count} players for team {team_data['mlb_name']}")
        
        print(f"Successfully saved {total_players} players to Firestore")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    main()