from uuid import UUID
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.repositories.integration import integration_repo
from app.services.oauth import oauth_service
from app.integrations.manager import ConnectorManager
from app.schemas.integration import NormalizedDocument
from app.core.exceptions import AppException

class IntegrationService:
    async def list_google_drive_files(
        self, db: AsyncSession, user_id: UUID, page_token: Optional[str] = None
    ) -> Tuple[List[NormalizedDocument], Optional[str]]:
        """
        List files from a user's connected Google Drive account.
        Automatically refreshes the token if expired.
        """
        # Get integration
        integration = await integration_repo.get_by_provider_and_user(
            db, provider="google_drive", user_id=user_id
        )
        if not integration or integration.status != "CONNECTED":
            raise AppException("Google Drive integration not found or not connected", status_code=404)

        # Check token expiration
        expires_at_str = integration.credentials.get("expires_at") if integration.credentials else None
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) >= expires_at:
                    integration = await oauth_service.refresh_google_token(db, integration)
            except Exception:
                # If parsing fails, attempt a refresh to be safe
                try:
                    integration = await oauth_service.refresh_google_token(db, integration)
                except Exception as refresh_error:
                    raise AppException(f"Failed to refresh token: {str(refresh_error)}", status_code=401)
        
        # In case there's no expiration data but token fails later, connector will raise Exception
        
        # Instantiate connector
        try:
            connector = ConnectorManager.get_connector(integration)
        except ValueError as e:
            raise AppException(f"Connector error: {str(e)}", status_code=500)
        
        # Fetch documents
        try:
            documents, next_page_token = await connector.fetch_documents(page_token=page_token)
            return documents, next_page_token
        except ValueError as e:
            raise AppException(f"Authentication failed with provider: {str(e)}", status_code=401)
        except Exception as e:
            raise AppException(f"Error communicating with Google Drive: {str(e)}", status_code=500)

integration_service = IntegrationService()
