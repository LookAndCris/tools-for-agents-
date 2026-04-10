"""Authentication dependency — resolves X-User-ID header to UserContext.

This is a FastAPI ``Depends()`` function, NOT a middleware class.
Using a dependency makes it trivial to override in tests via
``app.dependency_overrides``.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.user_context import UserContext
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.session import get_session
from infrastructure.repositories.pg_client_repo import PgClientRepository
from infrastructure.repositories.pg_staff_repo import PgStaffRepository


async def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    session: AsyncSession = Depends(get_session),
) -> UserContext:
    """Parse ``X-User-ID`` header and resolve the caller's ``UserContext``.

    Steps:
    1. Validate the header exists and is a valid UUID.
    2. Query ``users JOIN roles`` to get the user's role name.
    3. If role is ``staff``: look up the staff profile to get ``staff_id``.
    4. If role is ``client``: look up the client profile to get ``client_id``.
    5. Return a ``UserContext`` with all resolved IDs.

    Raises:
        HTTPException(401): If the header is missing, not a valid UUID, or the
            user is not found in the database.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid X-User-ID header",
    )

    # --- 1. Validate header presence and UUID format ---
    if x_user_id is None:
        raise _unauthorized

    try:
        user_uuid = UUID(x_user_id)
    except ValueError:
        raise _unauthorized

    # --- 2. Query users JOIN roles ---
    stmt = (
        select(UserModel)
        .join(RoleModel, UserModel.role_id == RoleModel.id)
        .where(UserModel.id == user_uuid)
        .where(UserModel.is_active.is_(True))
    )
    result = await session.execute(stmt)
    user_model = result.scalar_one_or_none()

    if user_model is None:
        raise _unauthorized

    # Load the role eagerly (it was joined above but lazy-loaded by relationship)
    role_stmt = select(RoleModel).where(RoleModel.id == user_model.role_id)
    role_result = await session.execute(role_stmt)
    role_model = role_result.scalar_one_or_none()

    if role_model is None:
        raise _unauthorized

    role_name = role_model.name
    staff_id: UUID | None = None
    client_id: UUID | None = None

    # --- 3. Resolve staff_id / client_id ---
    if role_name == "staff":
        staff_repo = PgStaffRepository(session)
        staff = await staff_repo.get_by_user_id(user_uuid)
        if staff is not None:
            staff_id = staff.id

    elif role_name == "client":
        client_repo = PgClientRepository(session)
        client = await client_repo.get_by_user_id(user_uuid)
        if client is not None:
            client_id = client.id

    return UserContext(
        user_id=user_uuid,
        role=role_name,
        staff_id=staff_id,
        client_id=client_id,
    )
