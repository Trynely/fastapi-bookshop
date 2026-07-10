import logging
import sys

COLORS = {
    "DEBUG":    "\033[36m",    # cyan
    "INFO":     "\033[32m",    # green
    "WARNING":  "\033[33m",    # yellow
    "ERROR":    "\033[31m",    # red
    "CRITICAL": "\033[1;31m",  # bold red
    "RESET":    "\033[0m",
    "DIM":      "\033[2m",
    "BOLD":     "\033[1m",
}

class ColorFormatter(logging.Formatter):
    def format(self, record):
        level_color = COLORS.get(record.levelname, COLORS["RESET"])
        reset = COLORS["RESET"]
        dim = COLORS["DIM"]
        bold = COLORS["BOLD"]

        record.levelname = f"{level_color}{record.levelname:<8}{reset}"
        record.name = f"{bold}{record.name}{reset}"
        record.msg = f"{record.msg}"

        self._style._fmt = (
            f"{dim}%(asctime)s{reset} "
            f"%(levelname)s "
            f"%(name)s {dim}|{reset} "
            f"%(message)s"
        )
        return super().format(record)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,  # перезаписывает дефолтный хэндлер uvicorn
    )

    # убираем спам от сторонних либ
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)