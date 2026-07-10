# app/admin/utils/model_sync_checker.py

import logging
from typing import Type
from sqladmin import ModelView
from sqlalchemy import inspect as sa_inspect
from app.core.config.base import get_settings

settings = get_settings()
logger = logging.getLogger(settings.app.name)


def _get_model_columns(view: Type[ModelView]) -> set[str]:
    """Получает все колонки SQLAlchemy модели."""
    model = view.model
    mapper = sa_inspect(model)
    cols = {col.key for col in mapper.columns}
    rels = {rel.key for rel in mapper.relationships}
    return cols | rels


def _get_view_declared_fields(view: Type[ModelView]) -> dict[str, set[str]]:
    """Собирает все поля, объявленные в ModelView по категориям."""
    declared: dict[str, set[str]] = {}

    attrs_to_check = {
        "column_list": "column_list",
        "column_details_list": "column_details_list",
        "column_details_exclude_list": "column_details_exclude_list",
        "form_columns": "form_columns",
        "column_searchable_list": "column_searchable_list",
        "column_sortable_list": "column_sortable_list",
        "column_labels": "column_labels (keys)",
        "column_formatters": "column_formatters (keys)",
    }

    for attr, label in attrs_to_check.items():
        raw = getattr(view, attr, None)
        if not raw:
            continue

        # column_labels и column_formatters — это dict, берём ключи
        if isinstance(raw, dict):
            raw = list(raw.keys())

        fields = set()
        for item in raw:
            # Может быть строкой ("title") или атрибутом модели (BookModel.title)
            if isinstance(item, str):
                fields.add(item)
            elif hasattr(item, "key"):
                fields.add(item.key)
            else:
                # InstrumentedAttribute через __str__ даёт "Model.field"
                fields.add(str(item).split(".")[-1])

        declared[label] = fields

    return declared


def check_admin_model_sync(views: list[Type[ModelView]]) -> None:
    for view in views:
        model_fields = _get_model_columns(view)
        declared = _get_view_declared_fields(view)
        view_name = view.__name__

        ignored = set(getattr(view, "admin_ignored_fields", []))

        # 1. Поля в view, которых нет в модели
        for section, fields in declared.items():
            unknown = fields - model_fields
            if unknown:
                logger.warning(
                    "⚠️  [AdminSync] %s → секция '%s' содержит поля, "
                    "которых нет в модели %s: %s. "
                    "Обновите admin view!",
                    view_name,
                    section,
                    view.model.__name__,
                    sorted(unknown),
                )

        # 2. Поля в модели, которых нет в view и не в ignored
        all_declared = set()
        for fields in declared.values():
            all_declared |= fields

        missing_in_admin = model_fields - all_declared - ignored
        if missing_in_admin:
            logger.warning(
                "⚠️  [AdminSync] %s → поля модели %s отсутствуют "
                "в admin view и не добавлены в admin_ignored_fields: %s.",
                view_name,
                view.model.__name__,
                sorted(missing_in_admin),
            )