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
Extension module adding support for using linkd-based dependency injection with `Quart <https://quart.palletsprojects.com/en/latest/>`_.

See the examples directory for a full working application using this module.

.. note::
    Unlike the ``FastAPI`` and ``Starlette`` integrations, the default :meth:`~linkd.solver.inject` method
    will work for route handlers when using this extension.

----
"""

from __future__ import annotations

__all__ = ["Contexts", "DiContextMiddleware"]

import typing as t

from linkd import context as _context
from linkd.ext import _common

if t.TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from hypercorn.typing import ASGIReceiveCallable
    from hypercorn.typing import ASGISendCallable
    from hypercorn.typing import Scope

    from linkd import solver

    ASGIApp = Callable[[Scope, ASGIReceiveCallable, ASGISendCallable], Awaitable[None]]


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd.ext.quart uses."""

    __slots__ = ()

    ROOT = _context.Contexts.ROOT
    """The root DI context - ALL other contexts are built with this as the parent."""
    REQUEST = _common.REQUEST_CONTEXT
    """DI context used during HTTP request handling."""


class DiContextMiddleware:
    """
    Middleware class which handles setting up a DI context for each HTTP request.

    Args:
        app: The ASGI app this middleware will be applied to.
        manager: The dependency injection manager to use when entering the DI context.

    Example:

        .. code-block:: python

            import quart
            import linkd

            manager = linkd.DependencyInjectionManager()

            app = quart.Quart(__name__)
            app.asgi_app = linkd.ext.quart.DiContextMiddleware(app.asgi_app, manager)
    """

    __slots__ = ("app", "manager")

    def __init__(self, app: ASGIApp, manager: solver.DependencyInjectionManager) -> None:
        self.app: ASGIApp = app
        self.manager: solver.DependencyInjectionManager = manager

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async with self.manager.enter_context(Contexts.ROOT), self.manager.enter_context(Contexts.REQUEST):
            await self.app(scope, receive, send)
