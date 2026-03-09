import io
import json
import os
from datetime import datetime, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


class DriveStorage:
    """Google Drive backed project storage."""

    def __init__(self) -> None:
        self.root_folder_name = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_NAME", "InvestorAgentProjects")
        self.root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if creds_json:
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
        elif creds_path:
            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
        else:
            raise ValueError(
                "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON for Drive access.")

        self.service = build("drive", "v3", credentials=creds)
        if not self.root_folder_id:
            self.root_folder_id = self._ensure_folder(self.root_folder_name, None)

    def _list(self, query: str) -> list[dict[str, Any]]:
        resp = self.service.files().list(
            q=query,
            fields="files(id,name,mimeType,parents,createdTime,modifiedTime)",
            pageSize=1000,
        ).execute()
        return resp.get("files", [])

    def _ensure_folder(self, name: str, parent_id: str | None) -> str:
        escaped = name.replace("'", "\\'")
        parent_query = f"'{parent_id}' in parents and " if parent_id else ""
        q = (
            f"{parent_query}name='{escaped}' and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        files = self._list(q)
        if files:
            return files[0]["id"]
        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]
        folder = self.service.files().create(body=body, fields="id").execute()
        return folder["id"]

    def list_projects(self) -> list[dict[str, str]]:
        q = (
            f"'{self.root_folder_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        files = self._list(q)
        return [{"id": x["id"], "name": x["name"]} for x in sorted(files, key=lambda y: y["name"].lower())]

    def ensure_project(self, project_name: str) -> dict[str, str]:
        project_id = self._ensure_folder(project_name, self.root_folder_id)
        self._ensure_project_basics(project_id)
        return {"id": project_id, "name": project_name}

    def _ensure_project_basics(self, project_id: str) -> None:
        for fname, default in [
            ("saved_configs.json", []),
            ("runs.jsonl", ""),
            ("meta.json", {"updated_at": self._now()}),
        ]:
            if self._find_file(project_id, fname) is None:
                self.write_json(project_id, fname, default)

    def _find_file(self, parent_id: str, name: str) -> str | None:
        escaped = name.replace("'", "\\'")
        q = f"'{parent_id}' in parents and name='{escaped}' and trashed=false"
        files = self._list(q)
        return files[0]["id"] if files else None

    def _download_text(self, file_id: str) -> str:
        req = self.service.files().get_media(fileId=file_id)
        out = io.BytesIO()
        downloader = MediaIoBaseDownload(out, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return out.getvalue().decode("utf-8")

    def _upload_text(self, parent_id: str, name: str, content: str, mime_type: str = "application/json") -> str:
        existing_id = self._find_file(parent_id, name)
        media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype=mime_type, resumable=False)
        if existing_id:
            self.service.files().update(fileId=existing_id, media_body=media).execute()
            return existing_id
        body: dict[str, Any] = {"name": name, "parents": [parent_id]}
        created = self.service.files().create(body=body, media_body=media, fields="id").execute()
        return created["id"]

    def read_json(self, project_id: str, name: str, fallback: Any) -> Any:
        file_id = self._find_file(project_id, name)
        if not file_id:
            return fallback
        raw = self._download_text(file_id)
        if not raw.strip():
            return fallback
        return json.loads(raw)

    def write_json(self, project_id: str, name: str, data: Any) -> str:
        return self._upload_text(project_id, name, json.dumps(data, ensure_ascii=False, indent=2), "application/json")

    def append_jsonl(self, project_id: str, name: str, record: dict[str, Any]) -> str:
        file_id = self._find_file(project_id, name)
        line = json.dumps(record, ensure_ascii=False) + "\n"
        if file_id:
            existing = self._download_text(file_id)
            combined = existing + line
        else:
            combined = line
        return self._upload_text(project_id, name, combined, "application/json")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
