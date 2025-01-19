import requests
import json

def download_highlights(game_id):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/content"
    data = requests.get(url).json()
    
    # Use the correct path for highlights
    highlights = data.get("highlights", {}).get("highlights", {}).get("items", [])
    if not highlights:
        print(f"No highlights found for game {game_id}")
        return
    
    print(f"Found {len(highlights)} highlight(s) for game {game_id}:\n")
    for i, clip in enumerate(highlights, start=1):
        title = clip.get("headline", "No Title")
        playbacks = clip.get("playbacks", [])
        keywords = clip.get("keywordsAll", [])
        should_skip = False
        date = clip.get("date", "")
        if clip.get("type") != "video":
            continue
        for keyword in keywords:
            if keyword.get("type") == "taxonomy":
                if keyword.get("value") == "interview":
                    # skip interview highlights
                    print(f"Skipping interview highlights for game {title}")
                    should_skip = True
                    break
        if should_skip:
            continue
        
        if not playbacks:
            print(f"{i}. {title}")
            print("   No video playbacks available.\n")
            continue
        
        # Typically the last playback is high quality MP4, or you might pick "mp4Avc"

        playbacks = clip.get("playbacks", [])
        if not playbacks:
            print(f"{i}. {title}")
            print("   No video playbacks available.\n")
            continue
        
        # STEP 1: Try to find mp4Avc
        mp4_url = None
        for pb in playbacks:
            if pb.get("name") == "mp4Avc":
                mp4_url = pb["url"]
                break
        
        # STEP 2: If we didn’t find mp4Avc, maybe look for 'highBit'
        if not mp4_url:
            for pb in playbacks:
                if pb.get("name") == "highBit":
                    mp4_url = pb["url"]
                    break
        
        # STEP 3: If still None, fallback to last playback in list
        if not mp4_url:
            mp4_url = playbacks[-1].get("url")
        
        print(f"{i}. {title}")
        print(f"   Video URL: {mp4_url}\n")
        
        
        print(f"{i}. {title}")
        print(f"   Video URL: {mp4_url}\n")
        print(f"   Date: {date}\n")
        
        # If you want to actually download the clip:
        # video_data = requests.get(clip_url).content
        # with open(f"{title}.mp4", "wb") as f:
        #     f.write(video_data)


if __name__ == "__main__":
    # Example: game 717540 from the 2023 season (modify to any known past game)
    download_highlights(748266)
