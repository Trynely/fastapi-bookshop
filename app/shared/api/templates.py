from fastapi.templating import Jinja2Templates
from app.core.config.base import get_settings

settings = get_settings()

templates = Jinja2Templates(directory=str(settings.app.templates_dir))

# доступно во всех шаблонах: {{ api_prefix }}
templates.env.globals["api_prefix"] = settings.api.prefix
