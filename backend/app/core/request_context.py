"""Per-request context (request id, client ip, user agent) stored in a contextvar by the middleware."""

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass
class RequestContext:
    request_id: str = ""
    ip: str | None = None
    user_agent: str | None = None


_ctx: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())


def set_request_context(ctx: RequestContext) -> Token:
    return _ctx.set(ctx)


def reset_request_context(token: Token) -> None:
    _ctx.reset(token)


def get_request_context() -> RequestContext:
    return _ctx.get()
