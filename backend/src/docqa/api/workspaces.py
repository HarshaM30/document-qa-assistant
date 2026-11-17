"""Workspace CRUD, scoped to the signed-in user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.auth.deps import CurrentUser, DbDep
from docqa.db.models import User, Workspace
from docqa.schemas.workspaces import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

_DUPLICATE_NAME = "You already have a workspace with this name"


async def get_owned_workspace(db: AsyncSession, user: User, workspace_id: uuid.UUID) -> Workspace:
    """Return the workspace if the user owns it; 404 otherwise (never reveal it exists)."""
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


@router.get("")
async def list_workspaces(user: CurrentUser, db: DbDep) -> list[WorkspaceOut]:
    rows = await db.execute(
        select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.created_at)
    )
    return [WorkspaceOut.model_validate(w) for w in rows.scalars()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace(body: WorkspaceCreate, user: CurrentUser, db: DbDep) -> WorkspaceOut:
    workspace = Workspace(owner_id=user.id, name=body.name)
    db.add(workspace)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_DUPLICATE_NAME) from None
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: uuid.UUID, user: CurrentUser, db: DbDep) -> WorkspaceOut:
    return WorkspaceOut.model_validate(await get_owned_workspace(db, user, workspace_id))


@router.patch("/{workspace_id}")
async def rename_workspace(
    workspace_id: uuid.UUID, body: WorkspaceUpdate, user: CurrentUser, db: DbDep
) -> WorkspaceOut:
    workspace = await get_owned_workspace(db, user, workspace_id)
    workspace.name = body.name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_DUPLICATE_NAME) from None
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: uuid.UUID, user: CurrentUser, db: DbDep) -> None:
    workspace = await get_owned_workspace(db, user, workspace_id)
    await db.delete(workspace)
    await db.commit()
