from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import ValidationError

from time_radio.errors import ExternalServiceError

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    service: str,
    attempts: int,
    delays_seconds: tuple[float, ...],
) -> T:
    if attempts < 1:
        raise ValueError("Retry attempts must be at least one.")
    if len(delays_seconds) != max(0, attempts - 1):
        raise ValueError("Retry delays must match the number of retry attempts.")

    last_error: ExternalServiceError | ValidationError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except (ExternalServiceError, ValidationError) as error:
            last_error = error
            if attempt == attempts:
                break
            logger.warning(
                "External operation failed and will be retried",
                extra={
                    "service": service,
                    "attempt": attempt,
                    "maximum_attempts": attempts,
                    "error_type": type(error).__name__,
                },
            )
            await asyncio.sleep(delays_seconds[attempt - 1])

    if last_error is None:
        raise RuntimeError("Retry operation ended without a result or captured error.")
    raise last_error

