# -*- coding: utf-8 -*-
# Copyright (c) 2025-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Extension module adding support for using linkd-based dependency injection with `Starlette <https://www.starlette.io/>`_.

See the examples directory for a full working application using this module.

----
"""

from __future__ import annotations

__all__ = ["Contexts", "DiContextMiddleware", "RequestContainer", "RootContainer", "inject"]

import typing as t

from linkd import context as _context
from linkd import solver as _solver
from linkd.context import RootContainer
from linkd.ext import _common
from linkd.ext._common import RequestContainer

if t.TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd.ext.fastapi uses."""

    __slots__ = ()

    ROOT = _context.Contexts.ROOT
    """The root DI context - ALL other contexts are built with this as the parent."""
    REQUEST = _common.REQUEST_CONTEXT
    """DI context used during HTTP request handling."""


try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class DiContextMiddleware(BaseHTTPMiddleware):
        """
        Middleware class which handles setting up a DI context for each HTTP request.

        Args:
            app: The app this middleware will be applied to.
            manager: The dependency injection manager to use when entering the DI context.

        Example:

            .. code-block:: python

                from starlette.applications import Starlette
                from starlette.middleware import Middleware
                import linkd

                manager = linkd.DependencyInjectionManager()

                middleware = [
                    Middleware(linkd.ext.starlette.DiContextMiddleware, manager=manager),
                ]

                app = Starlette(routes=..., lifetime=..., middleware=middleware)
        """

        __slots__ = ("app", "manager")

        def __init__(self, app: ASGIApp, manager: _solver.DependencyInjectionManager) -> None:
            super().__init__(app)
            self.manager: _solver.DependencyInjectionManager = manager

        async def dispatch(self, request: Request, call_next: t.Callable[[Request], t.Awaitable[Response]]) -> Response:
            async with self.manager.enter_context(Contexts.ROOT), self.manager.enter_context(Contexts.REQUEST) as rc:
                rc.add_value(Request, request)
                return await call_next(request)
except ImportError:
    if not t.TYPE_CHECKING:

        class DiContextMiddleware:
            __slots__ = ()

            def __init__(self, *args: t.Any) -> None:
                raise RuntimeError("starlette is not installed - starlette middleware is not available")


def inject(func: _common.InjectedCallableT) -> _common.InjectedCallableT:
    """
    Specialised decorator enabling linkd dependency injection for starlette route handlers. This
    decorator must be used instead of the standard :meth:`~linkd.solver.inject` decorator so that
    starlette does not treat injection-enabled functions as ASGI apps instead of request/response functions.

    If you are enabling DI for any function other than a route handler then the standard decorator will still work.

    Args:
        func: The function to enable DI for.

    Returns:
        The function with dependency injection enabled.

    Note:
        ASGI route handlers are not supported when using this decorator, you should use the standard
        :meth:`~linkd.solver.inject` decorator instead.

    Example:

        .. code-block:: python

            from starlette.applications import Starlette
            from starlette.middleware import Middleware
            from starlette.requests import Request
            from starlette.responses import Response
            from starlette.routing import Route

            import linkd

            @linkd.ext.starlette.inject
            async def some_handler(request: Request, dependency: SomeDependency) -> Response:
                ...

            routes = [
                Route("/foo", some_handler),
            ]

            manager = linkd.DependencyInjectionManager()

            middleware = [
                Middleware(linkd.ext.starlette.DiContextMiddleware, manager=manager),
            ]

            app = Starlette(routes=routes, lifetime=..., middleware=middleware)
    """
    func = _solver.inject(func)

    async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        return await func(*args, **kwargs)

    # sorry pyright :/
    return wrapper  # type: ignore[reportReturnType]
