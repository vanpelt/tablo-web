"""In-memory ring buffer for recent log lines used by the debug report."""

import logging
from collections import deque

recent_logs: deque[str] = deque(maxlen=200)


class _BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            recent_logs.append(self.format(record))
        except Exception:
            pass


def install() -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()

    handler = _BufferHandler()
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # The root logger defaults to WARNING, so without this every log.info()
    # in the app was dropped before it reached the buffer above — the debug
    # report collected uvicorn's lines and none of our own.
    root.setLevel(logging.INFO)

    # uvicorn only attaches handlers to its own loggers, and those do not
    # propagate, so app messages reached no stream at all. One StreamHandler
    # here puts them in `docker compose logs` without duplicating uvicorn's.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        root.addHandler(stream)
