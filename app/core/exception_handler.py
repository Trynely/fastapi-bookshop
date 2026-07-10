from fastapi import Request
from fastapi.responses import ORJSONResponse
from app.shared.exception import AppException

async def exception_handler(request: Request, exc: AppException) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.code,
        content={"detail": exc.msg},
    )