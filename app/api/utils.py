from fastapi import Request, HTTPException
from firebase_admin import auth
from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

security = HTTPBearer()


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )
