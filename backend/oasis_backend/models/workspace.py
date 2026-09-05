"""
Workspace and Monaco editor data models.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class FileNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    children: Optional[List[FileNode]] = None
    size_bytes: Optional[int] = None


class WorkspaceCreateRequest(BaseModel):
    repo_url: str
    issue_number: int


class WorkspaceSession(BaseModel):
    id: str
    workspace_id: Optional[str] = None
    user_id: int
    repo_url: str
    repo_full_name: str
    issue_number: int
    branch_name: str
    relevant_files: List[str] = Field(default_factory=list)
    status: str
    created_at: str
    last_accessed_at: str

    def __init__(self, **data):
        if "id" in data and "workspace_id" not in data:
            data["workspace_id"] = data["id"]
        elif "workspace_id" in data and "id" not in data:
            data["id"] = data["workspace_id"]
        super().__init__(**data)


class FileContentResponse(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    size_bytes: int


class SaveFileRequest(BaseModel):
    path: str
    content: str


class SaveFileResponse(BaseModel):
    path: str
    saved: bool
    bytes_written: int


class WorkspaceDiffResponse(BaseModel):
    diff: str
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
