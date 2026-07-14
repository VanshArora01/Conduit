from typing import Any, Dict
import httpx
import jwt
import urllib.parse
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.integration import Integration
from app.repositories.integration import integration_repo
from sqlalchemy.ext.asyncio import AsyncSession

class OAuthService:
    def __init__(self):
        self.settings = get_settings()

    def generate_state_token(self, user_id: UUID) -> str:
        """
        Generate a signed JWT state token to prevent CSRF and correlate the callback.
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "oauth_state"
        }
        return jwt.encode(payload, self.settings.JWT_SECRET_KEY, algorithm=self.settings.JWT_ALGORITHM)

    def verify_state_token(self, state: str) -> UUID:
        """
        Verify the state token and extract the user_id.
        """
        try:
            payload = jwt.decode(state, self.settings.JWT_SECRET_KEY, algorithms=[self.settings.JWT_ALGORITHM])
            if payload.get("type") != "oauth_state":
                raise AppException("Invalid state token type", status_code=status.HTTP_400_BAD_REQUEST)
            return UUID(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise AppException("OAuth state token expired. Please try connecting again.", status_code=status.HTTP_400_BAD_REQUEST)
        except Exception:
            raise AppException("Invalid OAuth state token.", status_code=status.HTTP_400_BAD_REQUEST)

    def get_google_auth_url(self, user_id: UUID) -> str:
        """
        Generate the Google OAuth consent screen URL.
        """
        if not self.settings.GOOGLE_CLIENT_ID:
            raise AppException("Google OAuth is not configured on the server.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        state = self.generate_state_token(user_id)
        
        # Scopes required for Google Drive (read-only for now)
        scopes = [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        params = {
            "client_id": self.settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self.settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",  # Force consent to ensure we get a refresh token
            "state": state
        }
        
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        return url

    async def exchange_google_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange the authorization code for tokens.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.GOOGLE_CLIENT_ID,
                    "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.GOOGLE_REDIRECT_URI
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise AppException(f"Failed to exchange token: {response.text}", status_code=status.HTTP_400_BAD_REQUEST)
                
            return response.json()

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch the user's profile info from Google.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise AppException(f"Failed to fetch user info: {response.text}", status_code=status.HTTP_400_BAD_REQUEST)
                
            return response.json()

    async def handle_google_callback(self, db: AsyncSession, code: str, state: str) -> Integration:
        """
        Process the OAuth callback: verify state, exchange token, and store credentials.
        """
        user_id = self.verify_state_token(state)
        token_data = await self.exchange_google_code(code)
        user_info = await self.get_google_user_info(token_data["access_token"])
        
        external_account_id = user_info["id"]
        email = user_info.get("email")
        
        # Calculate expiry
        expires_in = token_data.get("expires_in", 3599)
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        
        credentials = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
            "account_email": email
        }
        
        # Check if we already have this integration
        existing = await integration_repo.get_by_provider_and_user(db, provider="google_drive", user_id=user_id)
        
        if existing:
            # If refresh_token is missing in the new payload (because prompt wasn't consent), preserve the old one
            if not credentials["refresh_token"] and existing.credentials and existing.credentials.get("refresh_token"):
                credentials["refresh_token"] = existing.credentials.get("refresh_token")
                
            # Update credentials
            existing.credentials = credentials
            existing.external_account_id = external_account_id
            existing.display_name = email or f"Google Drive ({external_account_id})"
            existing.status = "CONNECTED"
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new integration
            integration = await integration_repo.create(db, obj_in={
                "user_id": user_id,
                "provider": "google_drive",
                "display_name": email or f"Google Drive ({external_account_id})",
                "status": "CONNECTED",
                "external_account_id": external_account_id,
                "credentials": credentials,
                "settings": {}
            })
            return integration

    async def refresh_google_token(self, db: AsyncSession, integration: Integration) -> Integration:
        """
        Refresh the Google access token using the stored refresh token.
        """
        if not integration.credentials or not integration.credentials.get("refresh_token"):
            raise AppException("No refresh token available to refresh Google credentials", status_code=status.HTTP_400_BAD_REQUEST)
            
        refresh_token = integration.credentials["refresh_token"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.GOOGLE_CLIENT_ID,
                    "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise AppException(f"Failed to refresh Google token: {response.text}", status_code=status.HTTP_400_BAD_REQUEST)
                
            token_data = response.json()
            
            # Update credentials
            credentials = dict(integration.credentials)
            credentials["access_token"] = token_data["access_token"]
            
            if "refresh_token" in token_data:
                credentials["refresh_token"] = token_data["refresh_token"]
                
            expires_in = token_data.get("expires_in", 3599)
            credentials["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
            
            integration.credentials = credentials
            await db.commit()
            await db.refresh(integration)
            
            return integration

oauth_service = OAuthService()
