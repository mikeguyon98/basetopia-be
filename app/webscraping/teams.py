from google.cloud import firestore
import requests
import json
from datetime import datetime
import uuid
from dotenv import load_dotenv
import os

def initialize_firestore():
    """Initialize and return Firestore client."""
    return firestore.Client()

def fetch_mlb_teams():
    """Fetch teams data from MLB API."""
    teams_endpoint_url = 'https://statsapi.mlb.com/api/v1/teams?sportId=1'
    response = requests.get(teams_endpoint_url, timeout=10)
    data = json.loads(response.content)
    return data.get('teams', [])

def process_team_data(team):
    """Process raw team data into desired format."""
    # Generate unique ID and timestamp
    team_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    # Map and prefix fields
    processed_data = {
        'id': team_id,
        'created_at': created_at,
        'mlb_id': team.get('id'),
        'mlb_name': team.get('name'),
        'mlb_link': team.get('link'),
        'mlb_season': team.get('season'),
        'mlb_teamCode': team.get('teamCode'),
        'mlb_fileCode': team.get('fileCode'),
        'mlb_abbreviation': team.get('abbreviation'),
        'mlb_teamName': team.get('teamName'),
        'mlb_locationName': team.get('locationName'),
        'mlb_shortName': team.get('shortName'),
    }
    
    # Handle nested springLeague data
    spring_league = team.get('springLeague', {})
    processed_data.update({
        'mlb_springLeague_id': spring_league.get('id'),
        'mlb_springLeague_name': spring_league.get('name'),
        'mlb_springLeague_link': spring_league.get('link'),
        'mlb_springLeague_abbreviation': spring_league.get('abbreviation')
    })
    
    return processed_data

def save_teams_to_firestore(db, teams_data):
    """Save processed team data to Firestore."""
    batch = db.batch()
    teams_ref = db.collection('teams')
    
    for team in teams_data:
        processed_team = process_team_data(team)
        doc_ref = teams_ref.document(processed_team['id'])
        batch.set(doc_ref, processed_team)
    
    batch.commit()
    return len(teams_data)

def main():
    """Main function to orchestrate the data pipeline."""
    try:
        # Initialize Firestore
        load_dotenv()
        print(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        db = initialize_firestore()
        
        # Fetch teams data
        teams_data = fetch_mlb_teams()
        print("Fetched teams data")
        
        # Save to Firestore
        saved_count = save_teams_to_firestore(db, teams_data)
        
        print(f"Successfully saved {saved_count} teams to Firestore")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Tests
def test_fetch_mlb_teams():
    """Test MLB API fetch functionality."""
    teams = fetch_mlb_teams()
    assert len(teams) > 0
    assert 'id' in teams[0]
    assert 'name' in teams[0]

def test_process_team_data():
    """Test team data processing."""
    sample_team = {
        'id': 133,
        'name': 'Oakland Athletics',
        'link': '/api/v1/teams/133',
        'season': 2024,
        'teamCode': 'oak',
        'fileCode': 'oak',
        'abbreviation': 'OAK',
        'teamName': 'Athletics',
        'locationName': 'Oakland',
        'shortName': 'Oakland',
        'springLeague': {
            'id': 114,
            'name': 'Cactus League',
            'link': '/api/v1/league/114',
            'abbreviation': 'CL'
        }
    }
    
    processed = process_team_data(sample_team)
    
    assert 'id' in processed
    assert 'created_at' in processed
    assert processed['mlb_name'] == 'Oakland Athletics'
    assert processed['mlb_springLeague_name'] == 'Cactus League'

if __name__ == "__main__":
    main()