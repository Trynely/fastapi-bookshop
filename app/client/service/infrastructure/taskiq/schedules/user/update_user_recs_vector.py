import logging
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

logger = logging.getLogger(__name__)

@taskiq_broker.task(
    task_name="update_user_reco_vector_schedule",
    max_retries=3,
    retry_on_error=True,
)
async def update_user_reco_books_profile_schedule(user_id: int) -> None:
    from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfile
    from app.shared.service.infrastructure.dishka.base import get_container

    container = get_container()

    async with container() as request_container:
        user_personal_books_reco = await request_container.get(UserPersonalBooksRecoProfile)
        await user_personal_books_reco.build(user_id=user_id)