import requests
import json

def get_highlights(game_id):
    print(f"\nFetching highlights for game {game_id}")
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/content"
    data = None
    try:
        response = requests.get(url, timeout=500)
        print(response)
        response.raise_for_status()
        data = response.json()
        print(f"Successfully fetched content data for game {game_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game content: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

    # Use the correct path for highlights
    if not data.get("summary", {}).get("hasHighlightsVideo", False):
        return None
    highlights = data.get("highlights", {}).get("highlights", {}).get("items", [])
    if not highlights:
        print(f"No highlights found for game {game_id}")
        return None

    return_data = []
    print(f"\nProcessing {len(highlights)} highlights:")
    for i, clip in enumerate(highlights, start=1):
        print(f"\nProcessing highlight {i}/{len(highlights)}")
        
        title = clip.get("headline", "No Title")
        print(f"Title: {title}")
        
        if clip.get("type") != "video":
            print("Skipping: Not a video type highlight")
            continue

        keywords = clip.get("keywordsAll", [])
        should_skip = False
        for keyword in keywords:
            if keyword.get("type") == "taxonomy" and keyword.get("value") == "interview":
                print("Skipping: Interview highlight")
                should_skip = True
                break
        if should_skip:
            continue

        date = clip.get("date", "")
        playbacks = clip.get("playbacks", [])
        if not playbacks:
            print("No video playbacks available")
            continue

        # Find the best video URL
        mp4_url = None
        for pb in playbacks:
            if pb.get("name") == "mp4Avc":
                mp4_url = pb["url"]
                print("Found mp4Avc format")
                break
        
        if not mp4_url:
            for pb in playbacks:
                if pb.get("name") == "highBit":
                    mp4_url = pb["url"]
                    print("Found highBit format")
                    break
        
        if not mp4_url and playbacks:
            mp4_url = playbacks[-1].get("url")
            print("Using fallback video format")

        # Try to find jpg
        try:
            jpg = clip.get("image", {}).get("cuts", [])[0]
            print("Found image URL")
        except (IndexError, TypeError):
            print("No image URL found")
            continue

        return_data.append({
            "title": title,
            "video_url": mp4_url,
            "date": date,
            "image_url": jpg['src']
        })
        print(f"Successfully processed highlight: {title}")

    print(f"\nReturning {len(return_data)} processed highlights")
    return return_data

if __name__ == "__main__":
    # Example: game 717540 from the 2023 season (modify to any known past game)
    highlights = get_highlights(748236)
    print(highlights)