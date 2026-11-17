"""Tenancy: which documents and chunks a workspace may read.

Every retrieval query filters through `chunk_scope`, so a workspace only ever sees its own
uploads plus the library filings attached to it.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select

from docqa.db.models import Chunk, Document, DocumentStatus, WorkspaceLibraryDocument


def document_visible_to(workspace_id: uuid.UUID) -> Any:
    """Documents a workspace can see: its own uploads plus attached library filings."""
    attached = select(WorkspaceLibraryDocument.document_id).where(
        WorkspaceLibraryDocument.workspace_id == workspace_id
    )
    return or_(Document.workspace_id == workspace_id, Document.id.in_(attached))


def chunk_scope(workspace_id: uuid.UUID, index_config: str) -> Any:
    """Chunks of one index configuration in the workspace's ready documents."""
    visible = select(Document.id).where(
        document_visible_to(workspace_id), Document.status == DocumentStatus.READY
    )
    return (Chunk.index_config == index_config) & Chunk.document_id.in_(visible)
