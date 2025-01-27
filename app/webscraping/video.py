from moviepy import VideoFileClip, concatenate_videoclips
import requests
import os


def download_video(url, filename):
    """Download a video from a URL and save it locally"""
    response = requests.get(url, stream=True, headers={
                            "User-Agent": "Mozilla/5.0"}, timeout=1000)
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def combine_videos(video_urls, output_filename='combined_video.mp4'):
    """
    Combine multiple MP4 videos into a single clip

    Args:
        video_urls (list): List of URLs to MP4 videos
        output_filename (str): Name of the output video file
    """
    # Create temp directory if it doesn't exist
    if not os.path.exists('temp'):
        os.makedirs('temp')

    # Download all videos
    video_files = []
    for i, url in enumerate(video_urls):
        temp_filename = f'temp/video_{i}.mp4'
        download_video(url, temp_filename)
        video_files.append(temp_filename)

    # Load all video clips
    clips = [VideoFileClip(file) for file in video_files]

    # Concatenate all clips
    final_clip = concatenate_videoclips(clips)

    # Write the output file
    final_clip.write_videofile(output_filename)

    # Clean up
    final_clip.close()
    for clip in clips:
        clip.close()

    # Remove temporary files
    for file in video_files:
        os.remove(file)
    os.rmdir('temp')


# Example usage
if __name__ == "__main__":
    # Example list of MP4 URLs
    urls = [
        "https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-02/22/9c9c9ed7-8be01c3d-ead026ac-csvm-diamondx64-asset_1280x720_59_4000K.mp4",
        "https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-02/22/daa8bbb3-085bf866-3688cde0-csvm-diamondx64-asset_1280x720_59_4000K.mp4",
        " https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-02/22/68963373-3d772ebe-3f647d39-csvm-diamondx64-asset_1280x720_59_4000K.mp4"
    ]

    combine_videos(urls, "final_video.mp4")
