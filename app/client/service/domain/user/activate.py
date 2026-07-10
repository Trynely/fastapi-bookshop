from __future__ import annotations
from datetime import datetime, timezone
from app.client.db.postgres.models import ClientModel

def user_make_active(user: ClientModel) -> None:
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)