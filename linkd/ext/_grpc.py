# api_ref_gen::ignore
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
from __future__ import annotations

__all__ = ["Contexts", "DiInterceptor"]

import functools
import typing as t

import grpc
from google.protobuf import message
from grpc import aio as grpc_aio

from linkd import context as _context
from linkd import solver as _solver
from linkd.ext import _common

if t.TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from collections.abc import Awaitable
    from collections.abc import Callable

RequestT = t.TypeVar("RequestT", bound=message.Message)


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd.ext.grpc uses."""

    __slots__ = ()

    ROOT = _context.Contexts.ROOT
    """The root DI context - ALL other contexts are built with this as the parent."""
    REQUEST = _common.REQUEST_CONTEXT
    """DI context used during gRPC request handling."""


class DiInterceptor(grpc_aio.ServerInterceptor):
    """
    Server interceptor which handles setting up a DI context for each gRPC request.

    The :attr:`~Contexts.ROOT` and :attr:`~Contexts.REQUEST` contexts are entered for the duration of
    every RPC, across all four cardinalities (unary-unary, unary-stream, stream-unary, and stream-stream).
    Within the request context, the active :class:`grpc.ServicerContext` is registered as a dependency - as
    is the request message (:class:`google.protobuf.message.Message`) for the unary-request RPCs.

    Args:
        manager: The dependency injection manager to use when entering the DI context.

    Example:

        .. code-block:: python

            import grpc
            import linkd

            manager = linkd.DependencyInjectionManager()

            server = grpc.aio.server(interceptors=[linkd.ext.grpc.DiInterceptor(manager)])
    """

    def __init__(self, manager: _solver.DependencyInjectionManager) -> None:
        self._manager = manager

    async def __unary_unary(
        self,
        request: RequestT,
        context: grpc.ServicerContext,
        *,
        behaviour: Callable[[RequestT, grpc.ServicerContext], t.Any],
    ) -> t.Any:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as container,
        ):
            container.add_value(message.Message, request)
            container.add_value(grpc.ServicerContext, context)

            return await behaviour(request, context)

    async def __stream_unary(
        self,
        request_iterator: AsyncIterator[message.Message],
        context: grpc.ServicerContext,
        *,
        behaviour: Callable[..., t.Any],
    ) -> t.Any:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as container,
        ):
            container.add_value(grpc.ServicerContext, context)

            return await behaviour(request_iterator, context)

    async def __unary_stream(
        self,
        request: RequestT,
        context: grpc.ServicerContext,
        *,
        behaviour: Callable[[RequestT, grpc.ServicerContext], t.Any],
    ) -> t.Any:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as container,
        ):
            container.add_value(message.Message, request)
            container.add_value(grpc.ServicerContext, context)

            async for result in behaviour(request, context):
                yield result

    async def __stream_stream(
        self,
        request_iterator: AsyncIterator[message.Message],
        context: grpc.ServicerContext,
        *,
        behaviour: Callable[..., t.Any],
    ) -> t.Any:
        async with (
            self._manager.enter_context(Contexts.ROOT),
            self._manager.enter_context(Contexts.REQUEST) as container,
        ):
            container.add_value(grpc.ServicerContext, context)

            async for result in behaviour(request_iterator, context):
                yield result

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler[t.Any, t.Any]]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler[t.Any, t.Any] | None:
        rpc_handler = await continuation(handler_call_details)
        # rpc_handler will be None when the requested method is unknown - stubs don't reflect this
        if rpc_handler is None:  # type: ignore[reportUnnecessaryComparison]
            return rpc_handler

        if rpc_handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                functools.partial(self.__unary_unary, behaviour=rpc_handler.unary_unary),
                rpc_handler.request_deserializer,
                rpc_handler.response_serializer,
            )
        elif rpc_handler.stream_unary:
            return grpc.stream_unary_rpc_method_handler(
                functools.partial(self.__stream_unary, behaviour=rpc_handler.stream_unary),
                rpc_handler.request_deserializer,
                rpc_handler.response_serializer,
            )
        elif rpc_handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                functools.partial(self.__unary_stream, behaviour=rpc_handler.unary_stream),
                rpc_handler.request_deserializer,
                rpc_handler.response_serializer,
            )
        elif rpc_handler.stream_stream:
            return grpc.stream_stream_rpc_method_handler(
                functools.partial(self.__stream_stream, behaviour=rpc_handler.stream_stream),
                rpc_handler.request_deserializer,
                rpc_handler.response_serializer,
            )

        return rpc_handler
