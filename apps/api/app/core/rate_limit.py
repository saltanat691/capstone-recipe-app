"""
Process-wide rate limiter.

Defined in its own module so endpoint decorators can `from
app.core.rate_limit import limiter` without depending on `app.main` (which
would create an import cycle).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


# Per-route limits only; no global cap.
limiter = Limiter(key_func=get_remote_address, default_limits=[])