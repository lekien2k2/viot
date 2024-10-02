"""add role permission data

Revision ID: 24d5a0f27b28
Revises: 3d19e8d3338d
Create Date: 2024-10-01 14:20:07.039025

"""

from collections.abc import Sequence
from typing import Any

from alembic import op
from sqlalchemy import delete, insert, select
from sqlalchemy.orm.session import Session

from app.models import Permission, Role, RolePermission
from app.module.auth.constants import TEAM_ROLE_OWNER
from app.module.auth.permission import TeamRolePermission

# revision identifiers, used by Alembic.
revision: str = "24d5a0f27b28"
down_revision: str | None = "3d19e8d3338d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

permissions = [
    Permission(scope=p.scope, title=p.title, description=p.description)
    for p in [
        # Team Roles
        TeamRolePermission.READ,
        TeamRolePermission.MANAGE,
        TeamRolePermission.DELETE,
    ]
]

role_owner_ids_stmt = select(Role.id).where(Role.name == TEAM_ROLE_OWNER)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    print("Starting data migration for team role permissions")
    session = Session(bind=op.get_bind())

    # Add all permissions to the database
    print("Adding permissions to the database")
    session.add_all(permissions)
    session.flush()

    # Update team Owner role permissions
    print("Updating team Owner role permissions")
    role_owner_ids = session.execute(role_owner_ids_stmt).scalars().all()
    print("Team Owner role IDs:", role_owner_ids)

    values: list[dict[str, Any]] = []
    for permission in permissions:
        for role_id in role_owner_ids:
            values.append({"role_id": role_id, "permission_id": permission.id})

    if values:
        stmt = insert(RolePermission).values(values)
        session.execute(stmt)

    session.commit()
    print("Data migration for team role permissions completed")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    print("Starting data rollback for team role permissions")
    session = Session(bind=op.get_bind())

    role_owner_ids = session.execute(role_owner_ids_stmt).scalars().all()
    print("Team Owner role IDs:", role_owner_ids)

    scopes = [p.scope for p in permissions]
    permission_ids = (
        session.execute(select(Permission.id).where(Permission.scope.in_(scopes))).scalars().all()
    )
    print("Permission IDs:", permission_ids)

    stmt = delete(RolePermission).where(
        RolePermission.role_id.in_(role_owner_ids),
        RolePermission.permission_id.in_(permission_ids),
    )
    session.execute(stmt)

    stmt = delete(Permission).where(Permission.scope.in_(scopes))
    session.execute(stmt)
    session.commit()

    print("Data rollback for team role permissions completed")
    # ### end Alembic commands ###
