from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.services.oauth import oauth_service
from app.repositories.integration import integration_repo
from app.services.integration import integration_service
from app.schemas.integration import DocumentListResponse, DocumentImportRequest, DocumentImportResponse
from app.core.exceptions import AppException
from app.services.document_import import document_import_service
from typing import Optional

router = APIRouter()

@router.get("/google/connect")
async def connect_google_drive(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Initiate the Google Drive OAuth flow.
    """
    url = oauth_service.get_google_auth_url(current_user.id)
    return {"url": url}

@router.get("/google/callback")
async def google_drive_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle the OAuth callback from Google.
    """
    integration = await oauth_service.handle_google_callback(db, code, state)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Authentication Successful</title></head>
    <body>
        <script>
            if (window.opener) {{
                window.opener.postMessage({{ type: 'OAUTH_COMPLETE', integration_id: '{integration.id}', display_name: '{integration.display_name}' }}, '*');
                window.close();
            }} else {{
                document.body.innerHTML = 'Authentication successful! You can close this tab.';
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/google/status")
async def google_drive_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Check if the current user has a connected Google Drive integration.
    """
    integration = await integration_repo.get_by_provider_and_user(db, provider="google_drive", user_id=current_user.id)
    
    if integration and integration.status == "CONNECTED":
        return {
            "status": "CONNECTED",
            "integration_id": str(integration.id),
            "display_name": integration.display_name
        }
    
    return {"status": "DISCONNECTED"}

@router.get("/google/files", response_model=DocumentListResponse)
async def list_google_drive_files(
    page_token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    List files from the user's connected Google Drive.
    """
    documents, next_token = await integration_service.list_google_drive_files(
        db=db, user_id=current_user.id, page_token=page_token
    )
    return DocumentListResponse(documents=documents, next_page_token=next_token)

@router.post("/google/import", response_model=DocumentImportResponse)
async def import_google_drive_files(
    request: DocumentImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Import documents from Google Drive into Conduit.
    """
    integration = await integration_repo.get_by_provider_and_user(db, provider="google_drive", user_id=current_user.id)
    if not integration or integration.status != "CONNECTED":
        raise AppException("Google Drive integration not found or not connected", status_code=404)
        
    stats = await document_import_service.import_documents(
        db=db,
        user_id=current_user.id,
        integration=integration,
        file_ids=request.file_ids,
        background_tasks=background_tasks
    )
    
    return DocumentImportResponse(**stats)


@router.post("/google/disconnect")
async def disconnect_google_drive(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Disconnect Google Drive integration for the current user.
    """
    integration = await integration_repo.get_by_provider_and_user(db, provider="google_drive", user_id=current_user.id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    integration.status = "DISCONNECTED"
    integration.credentials = None
    db.add(integration)
    await db.commit()
    
    return {"status": "success", "message": "Google Drive disconnected successfully."}
