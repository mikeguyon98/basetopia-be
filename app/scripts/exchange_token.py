# app/scripts/exchange_token.py
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Get root directory
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env.test')


def exchange_token():
    API_KEY = os.getenv('GOOGLE_API_KEY')
    custom_token = os.getenv('TEST_USER_CUSTOM_TOKEN')

    url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key={
        API_KEY}"

    data = {
        "token": custom_token,
        "returnSecureToken": True
    }

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            id_token = response.json().get('idToken')
            if id_token:
                # Update .env.test with the new token
                with open(ROOT_DIR / '.env.test', 'r') as file:
                    lines = file.readlines()

                with open(ROOT_DIR / '.env.test', 'w') as file:
                    token_written = False
                    for line in lines:
                        if line.startswith('TEST_USER_ID_TOKEN='):
                            file.write(f'TEST_USER_ID_TOKEN={id_token}\n')
                            token_written = True
                        else:
                            file.write(line)
                    if not token_written:
                        file.write(f'TEST_USER_ID_TOKEN={id_token}\n')

                print("Successfully obtained and saved ID token")
                return id_token
            else:
                print("No idToken in response")
        else:
            print("Failed to exchange token")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


if __name__ == "__main__":
    print("Starting token exchange...")
    exchange_token()
