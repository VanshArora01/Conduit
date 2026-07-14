from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import httpx
from app.integrations.base import BaseConnector
from app.integrations.registry import ConnectorRegistry
from app.schemas.integration import NormalizedDocument

@ConnectorRegistry.register("google_drive")
class GoogleDriveConnector(BaseConnector):
    """
    Google Drive Connector.
    Uses stored credentials to interact with the Google Drive API.
    """

    async def connect(self) -> bool:
        """
        Verify the connection using stored credentials.
        """
        return await self.health_check()

    async def disconnect(self) -> bool:
        """
        Placeholder for disconnect logic.
        """
        return True

    async def sync(self) -> Dict[str, Any]:
        """
        Placeholder for syncing files.
        """
        raise NotImplementedError("Google Drive sync not implemented yet.")

    async def fetch_documents(self, page_token: Optional[str] = None) -> Tuple[List[NormalizedDocument], Optional[str]]:
        """
        Fetch documents from Google Drive.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("No access token available for Google Drive")

        access_token = self.credentials["access_token"]
        
        params = {
            "q": "trashed=false",
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink)",
            "pageSize": 100
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch files from Google Drive: {response.text}")

            data = response.json()
            raw_files = data.get("files", [])
            next_page_token = data.get("nextPageToken")

            documents = []
            for item in raw_files:
                is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
                
                modified_time_str = item.get("modifiedTime", "")
                if modified_time_str.endswith("Z"):
                    modified_time_str = modified_time_str[:-1] + "+00:00"
                
                try:
                    modified_at = datetime.fromisoformat(modified_time_str)
                except ValueError:
                    modified_at = datetime.now()
                    
                size_str = item.get("size")
                size = int(size_str) if size_str and size_str.isdigit() else None
                
                doc = NormalizedDocument(
                    id=item.get("id"),
                    external_id=item.get("id"),
                    title=item.get("name", "Untitled"),
                    provider="google_drive",
                    mime_type=item.get("mimeType", "application/octet-stream"),
                    modified_at=modified_at,
                    size=size,
                    web_view_link=item.get("webViewLink", ""),
                    is_folder=is_folder
                )
                documents.append(doc)

            return documents, next_page_token

    async def fetch_document(self, file_id: str) -> NormalizedDocument:
        """
        Fetch a single document from Google Drive.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("No access token available for Google Drive")

        access_token = self.credentials["access_token"]
        
        params = {
            "fields": "id, name, mimeType, modifiedTime, size, webViewLink"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch file {file_id} from Google Drive: {response.text}")

            item = response.json()
            is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
            
            modified_time_str = item.get("modifiedTime", "")
            if modified_time_str.endswith("Z"):
                modified_time_str = modified_time_str[:-1] + "+00:00"
            
            try:
                modified_at = datetime.fromisoformat(modified_time_str)
            except ValueError:
                modified_at = datetime.now()
                
            size_str = item.get("size")
            size = int(size_str) if size_str and size_str.isdigit() else None
            
            return NormalizedDocument(
                id=item.get("id"),
                external_id=item.get("id"),
                title=item.get("name", "Untitled"),
                provider="google_drive",
                mime_type=item.get("mimeType", "application/octet-stream"),
                modified_at=modified_at,
                size=size,
                web_view_link=item.get("webViewLink", ""),
                is_folder=is_folder
            )

    async def health_check(self) -> bool:
        """
        Check if the current stored credentials are valid by querying Google Drive API.
        """
        if not self.credentials or "access_token" not in self.credentials:
            return False
            
        access_token = self.credentials["access_token"]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
        except Exception:
            return False

    async def download_file(self, file_id: str, mime_type: str) -> bytes:
        """
        Download file contents from Google Drive.
        Handles both native Google Workspace documents (via export) and standard files (via alt=media).
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("No access token available for Google Drive")

        access_token = self.credentials["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        google_mime_types = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain"
        }

        async with httpx.AsyncClient() as client:
            if mime_type in google_mime_types:
                export_mime_type = google_mime_types[mime_type]
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType={export_mime_type}"
            else:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                raise Exception(f"Failed to download file {file_id}: {response.text}")

            return response.content

    async def list_folder_files_recursive(self, folder_id: str) -> list[NormalizedDocument]:
        """
        Recursively fetch all files inside a folder and all its subfolders.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("No access token available for Google Drive")

        access_token = self.credentials["access_token"]
        
        all_files = []
        folders_to_process = [folder_id]
        
        async with httpx.AsyncClient() as client:
            while folders_to_process:
                current_folder = folders_to_process.pop(0)
                page_token = None
                
                while True:
                    q = f"'{current_folder}' in parents and trashed = false"
                    params = {
                        "q": q,
                        "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink)",
                        "pageSize": 100
                    }
                    if page_token:
                        params["pageToken"] = page_token
                        
                    response = await client.get(
                        "https://www.googleapis.com/drive/v3/files",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to list folder files for {current_folder}: {response.text}")
                        break
                        
                    data = response.json()
                    files = data.get("files", [])
                    
                    for item in files:
                        is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
                        if is_folder:
                            folders_to_process.append(item.get("id"))
                        else:
                            # Parse dates and sizes
                            modified_time_str = item.get("modifiedTime", "")
                            if modified_time_str.endswith("Z"):
                                modified_time_str = modified_time_str[:-1] + "+00:00"
                            try:
                                modified_at = datetime.fromisoformat(modified_time_str)
                            except ValueError:
                                modified_at = datetime.now()
                            size_str = item.get("size")
                            size = int(size_str) if size_str and size_str.isdigit() else None
                            
                            doc = NormalizedDocument(
                                id=item.get("id"),
                                external_id=item.get("id"),
                                title=item.get("name", "Untitled"),
                                provider="google_drive",
                                mime_type=item.get("mimeType", "application/octet-stream"),
                                modified_at=modified_at,
                                size=size,
                                web_view_link=item.get("webViewLink", ""),
                                is_folder=False
                            )
                            all_files.append(doc)
                            
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
                        
        return all_files
