# core/limiter.py
"""
Shared SlowAPI rate limiter instance.
Import this in api/main.py (to register middleware) and in any router
that needs per-route limits.

Uses the client IP address as the rate-limit key. In production, ensure
your reverse proxy (nginx/caddy) sets X-Forwarded-For correctly, or swap
get_remote_address for a trusted proxy-aware key function.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
