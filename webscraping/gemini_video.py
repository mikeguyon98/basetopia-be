from google import genai
from google.genai import types
import argparse
from dotenv import load_dotenv
import os
from google.oauth2 import service_account

def generate(url, prompt):
  credentials = service_account.Credentials.from_service_account_file(
    'basetopia-b9302-firebase-adminsdk-i33cv-50c3703f8d.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
  print(credentials)
  client = genai.Client(
      vertexai=True,
      project="basetopia-b9302",
      location="us-central1"
  )

  video1 = types.Part.from_uri(
      file_uri=url,
      mime_type="video/mp4",
  )

  model = "gemini-2.0-flash-exp"
  contents = [
    types.Content(
      role="user",
      parts=[
        video1,
        types.Part.from_text(prompt)
      ]
    )
  ]
  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
  )
  
  return_value = ""
  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    return_value += chunk.text  # Changed from chunk.data[0].text to chunk.text
  return return_value

if __name__ == "__main__":
    load_dotenv()
    url = "https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-02/22/9c9c9ed7-8be01c3d-ead026ac-csvm-diamondx64-asset_1280x720_59_4000K.mp4"
    prompt = "Summarize the video"
    return_value = generate(url, prompt)
    print(return_value)




  