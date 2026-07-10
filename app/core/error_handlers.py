from fastapi import FastAPI
from app.core.exception_handler import exception_handler
from app.shared.exception import AppException

def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, exception_handler)