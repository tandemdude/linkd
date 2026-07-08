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
Extension module adding support for using linkd-based dependency injection with `ConnectRPC <https://connectrpc.com/>`_.

See the examples directory for a full working application using this module.

.. note::
    Unlike the ``FastAPI`` and ``Starlette`` integrations, the default :meth:`~linkd.solver.inject` method
    will work for method handlers when using this extension.

----
"""

from __future__ import annotations

__all__ = ["Contexts", "DiInterceptor"]

import typing as t

from linkd import context as _context
from linkd import solver as _solver
from linkd.ext import _common

if t.TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from collections.abc import Awaitable
    from collections.abc import Callable

    from connectrpc.request import RequestContext

REQ = t.TypeVar("REQ")
RES = t.TypeVar("RES")


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd.ext.connectrpc uses."""

    __slots__ = ()

    ROOT = _context.Contexts.ROOT
    """The root DI context - ALL other contexts are built with this as the parent."""
    REQUEST = _common.REQUEST_CONTEXT
    """DI context used during ConnectRPC request handling."""


class DiInterceptor:
    """
    Server interceptor which handles setting up a DI context for each ConnectRPC request.

    The :attr:`~Contexts.ROOT` and :attr:`~Contexts.REQUEST` contexts are entered for the duration of
    every RPC, across all four cardinalities (unary-unary, unary-stream, stream-unary, and stream-stream).
    Within the request context, the active :class:`connectrpc.request.RequestContext` is registered
    as a dependency - as is the request message (:class:`google.protobuf.message.Message`) for
    the unary-request RPCs.

    Args:
        manager: The dependency injection manager to use when entering the DI context.

    Example:

        .. code-block:: python

            import linkd

            manager = linkd.DependencyInjectionManager()

            server = YourASGIApplication(
                YourService(),
                interceptors=[linkd.ext.connectrpc.DiInterceptor(manager)],
            )
    """

    __slots__ = ("_m_type", "_manager", "_rc_type")

    def __init__(self, manager: _solver.DependencyInjectionManager) -> None:
        self._manager = manager

        from connectrpc.request import RequestContext
        from google.protobuf import message

        self._rc_type: t.Final[type[RequestContext[t.Any, t.Any]]] = RequestContext
        self._m_type: t.Final[type[message.Message]] = message.Message

    async def intercept_unary(
        self,
        call_next: Callable[[REQ, RequestContext[REQ, RES]], Awaitable[RES]],
        request: REQ,
        ctx: RequestContext[REQ, RES],
    ) -> RES:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as rc,
        ):
            rc.add_value(self._rc_type, ctx).add_value(self._m_type, request)
            return await call_next(request, ctx)

    async def intercept_client_stream(
        self,
        call_next: Callable[[AsyncIterator[REQ], RequestContext[REQ, RES]], Awaitable[RES]],
        request: AsyncIterator[REQ],
        ctx: RequestContext[REQ, RES],
    ) -> RES:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as rc,
        ):
            rc.add_value(self._rc_type, ctx)
            return await call_next(request, ctx)

    async def intercept_server_stream(
        self,
        call_next: Callable[[REQ, RequestContext[REQ, RES]], AsyncIterator[RES]],
        request: REQ,
        ctx: RequestContext[REQ, RES],
    ) -> AsyncIterator[RES]:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as rc,
        ):
            rc.add_value(self._rc_type, ctx).add_value(self._m_type, request)
            async for res in call_next(request, ctx):
                yield res  # noqa: ASYNC119

    async def intercept_bidi_stream(
        self,
        call_next: Callable[[AsyncIterator[REQ], RequestContext[REQ, RES]], AsyncIterator[RES]],
        request: AsyncIterator[REQ],
        ctx: RequestContext[REQ, RES],
    ) -> AsyncIterator[RES]:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as rc,
        ):
            rc.add_value(self._rc_type, ctx).add_value(self._rc_type, request)
            async for res in call_next(request, ctx):
                yield res  # noqa: ASYNC119


if t.TYPE_CHECKING:
    from connectrpc.interceptor import BidiStreamInterceptor
    from connectrpc.interceptor import ClientStreamInterceptor
    from connectrpc.interceptor import ServerStreamInterceptor
    from connectrpc.interceptor import UnaryInterceptor

    _: type[UnaryInterceptor] = DiInterceptor
    __: type[ClientStreamInterceptor] = DiInterceptor
    ___: type[ServerStreamInterceptor] = DiInterceptor
    ____: type[BidiStreamInterceptor] = DiInterceptor
