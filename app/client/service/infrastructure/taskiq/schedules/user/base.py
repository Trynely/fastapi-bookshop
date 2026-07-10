from abc import ABC, abstractmethod
from app.client.service.infrastructure.taskiq.schedules.user.update_user_recs_vector import update_user_reco_books_profile_schedule
from app.core.config.client.user.personal_book_reco import VECTOR_UPDATE_DELAY

class IUserSchedulesPublisher(ABC):
    @abstractmethod
    async def update_user_reco_profile(self, user_id: int) -> None:
        pass


class UserTaskiqSchedulesPublisher(IUserSchedulesPublisher):
    async def update_user_reco_profile(self, user_id: int) -> None:
        await (
            update_user_reco_books_profile_schedule.kicker().with_labels(
                delay=VECTOR_UPDATE_DELAY
            ).kiq(user_id)
        )