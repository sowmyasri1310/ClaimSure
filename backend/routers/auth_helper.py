import os
from fastapi import Header, HTTPException
from supabase import create_client, Client

def get_current_user(authorization: str = Header(None)) -> str:
    """
    Extracts the authorization token, validates it against Supabase, and returns the user ID.
    If Supabase environment variables are missing, falls back to 'test_user_id' for ease of testing.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # If not configured, allow mock auth for development
    if not url or not key:
        return "test_user_id"
        
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    try:
        # Extract JWT
        token = authorization.replace("Bearer ", "").strip()
        supabase_client: Client = create_client(url, key)
        user_response = supabase_client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid Supabase JWT Session")
        return user_response.user.id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {str(e)}")
