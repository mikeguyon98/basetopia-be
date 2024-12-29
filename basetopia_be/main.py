import firebase_admin
from firebase_admin import credentials, auth
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI()

# Initialize Firebase Admin with your credentials
cred = credentials.Certificate("basetopia-b9302-firebase-adminsdk-i33cv-50c3703f8d.json")
#basetopia-b9302-firebase-adminsdk-i33cv-50c3703f8d.json
firebase_admin.initialize_app(cred)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

async def verify_firebase_token(local_credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(local_credentials.credentials)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )

# Keep your existing endpoint
@app.post("/verify-token")
async def verify_token(request: Request):
    body = await request.json()
    token = body.get("idToken")
    try:
        decoded_token = auth.verify_id_token(token)
        return {"uid": decoded_token["uid"], "email": decoded_token["email"]}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# Add a protected endpoint example
@app.get("/protected")
async def protected_route(token_data: Annotated[dict, Depends(verify_firebase_token)]):
    return {
        "message": "This is a protected route",
        "user": {
            "uid": token_data.get("uid"),
            "email": token_data.get("email"),
        }
    }

# Add a user profile endpoint
@app.get("/user/profile")
async def get_user_profile(token_data: Annotated[dict, Depends(verify_firebase_token)]):
    try:
        user = auth.get_user(token_data['uid'])
        return {
            "uid": user.uid,
            "email": user.email,
            "displayName": user.display_name,
            "photoURL": user.photo_url,
            "emailVerified": user.email_verified
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
