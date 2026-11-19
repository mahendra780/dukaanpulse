from sqlalchemy import BigInteger, ForeignKey, event
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria


class WorkspaceScoped:
    """Declarative mixin for every business-owned record."""

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.workspace_id"),
        nullable=False,
        index=True,
    )


@event.listens_for(Session, "do_orm_execute")
def apply_workspace_scope(execute_state):
    """Apply the request workspace to every ORM business query.

    Request authentication sets ``session.info['workspace_id']`` before a
    business router executes. The criteria also covers relationship and alias
    loads, making it difficult for a future query to accidentally omit the
    tenant predicate.
    """
    workspace_id = execute_state.session.info.get("workspace_id")
    if workspace_id is None or not execute_state.is_select:
        return
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            WorkspaceScoped,
            lambda entity: entity.workspace_id == workspace_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def assign_workspace_to_new_business_rows(session, flush_context, instances):
    workspace_id = session.info.get("workspace_id")
    for instance in session.new:
        if not isinstance(instance, WorkspaceScoped):
            continue
        if workspace_id is None:
            raise RuntimeError("Business records require an authenticated workspace context.")
        if instance.workspace_id is None:
            instance.workspace_id = workspace_id
        elif instance.workspace_id != workspace_id:
            raise RuntimeError("Business records must belong to the authenticated workspace.")
