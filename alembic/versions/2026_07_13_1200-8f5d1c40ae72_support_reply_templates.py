"""support reply templates

Revision ID: 8f5d1c40ae72
Revises: 2c3a322990d4
Create Date: 2026-07-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8f5d1c40ae72'
down_revision: Union[str, None] = '2c3a322990d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TEMPLATES = [
    {
        "title": "Приветствие",
        "content": (
            "Здравствуйте! На связи поддержка Bookshop 📚 "
            "Уже изучаю ваш вопрос, одну минуту, пожалуйста."
        ),
    },
    {
        "title": "Уточнение номера заказа",
        "content": (
            "Подскажите, пожалуйста, номер заказа — "
            "я проверю его статус и сразу вернусь с ответом."
        ),
    },
    {
        "title": "Нужно время на проверку",
        "content": (
            "Мне потребуется немного времени, чтобы уточнить информацию. "
            "Пожалуйста, оставайтесь на связи — я напишу, как только всё проверю."
        ),
    },
    {
        "title": "Сроки доставки",
        "content": (
            "Обычно доставка занимает 2–5 рабочих дней после передачи заказа "
            "в службу доставки. Трек-номер придёт вам на почту, как только "
            "заказ будет отправлен."
        ),
    },
    {
        "title": "Условия возврата",
        "content": (
            "Вернуть книгу можно в течение 14 дней с момента получения, "
            "если она сохранила товарный вид. Оформить возврат можно "
            "в личном кабинете в разделе «Заказы»."
        ),
    },
    {
        "title": "Завершение диалога",
        "content": (
            "Рады были помочь! Если появятся ещё вопросы — пишите, "
            "мы всегда на связи. Хорошего дня! 😊"
        ),
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('support_reply_templates',
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_support_reply_templates')),
    sa.UniqueConstraint('title', name=op.f('uq_support_reply_templates_title'))
    )

    op.bulk_insert(
        sa.table(
            'support_reply_templates',
            sa.column('title', sa.String),
            sa.column('content', sa.Text),
        ),
        DEFAULT_TEMPLATES,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('support_reply_templates')
