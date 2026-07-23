import asyncio
import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.db.postgres import db_helper
from app.core.db.redis import get_redis

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["Health"])

# проба должна падать быстро: healthcheck-таймаут в compose — 5s,
# поэтому не ждём дефолтные connect-таймауты драйверов (10s+)
_CHECK_TIMEOUT_SEC = 2.0


@health_router.get(
    "/health",
    summary="Liveness probe",
    include_in_schema=False,
)
async def health() -> dict:
    """Живой ли процесс. Без обращений к зависимостям — для LB/k8s liveness."""
    return {"status": "ok"}


async def _check_postgres() -> None:
    async with db_helper.session_factory() as session:
        await session.execute(text("SELECT 1"))


async def _check_redis() -> None:
    await get_redis().ping()


@health_router.get(
    "/ready",
    summary="Readiness probe",
    include_in_schema=False,
)
async def ready(response: Response) -> dict:
    """Готов ли инстанс принимать трафик: проверяет критичные зависимости
    (Postgres, Redis). 503, если хоть одна недоступна — тогда LB/k8s
    уводит трафик с этого пода."""
    probes = {"postgres": _check_postgres, "redis": _check_redis}

    # проверки идут параллельно: worst-case время ответа — один таймаут,
    # а не их сумма
    results = await asyncio.gather(
        *(asyncio.wait_for(probe(), timeout=_CHECK_TIMEOUT_SEC) for probe in probes.values()),
        return_exceptions=True,
    )

    checks: dict[str, str] = {}
    healthy = True

    for name, result in zip(probes, results):
        if isinstance(result, BaseException):
            logger.warning("readiness: %s check failed: %s", name, result)
            checks[name] = "error"
            healthy = False
        else:
            checks[name] = "ok"

    response.status_code = (
        status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return {"status": "ok" if healthy else "degraded", "checks": checks}
