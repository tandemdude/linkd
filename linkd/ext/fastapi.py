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
Extension module adding support for using linkd-based dependency injection to FastAPI.

See the examples directory for a full working application using this module.

----
"""

from __future__ import annotations

__all__ = ["Contexts", "inject", "use_di_context_middleware"]

import inspect
import logging
import typing as t
from collections.abc import Callable

from linkd import container
from linkd import context
from linkd import solver

if t.TYPE_CHECKING:
    import fastapi

InjectedCallableT = t.TypeVar("InjectedCallableT", bound=Callable[..., t.Any])

LOGGER = logging.getLogger(__name__)

RequestContainer = t.NewType("RequestContainer", container.Container)
"""Injectable type representing the dependency container for the request context."""


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd.ext.fastapi uses."""

    __slots__ = ()

    DEFAULT = context.Contexts.DEFAULT
    """The base DI context - ALL other contexts are built with this as the parent."""
    REQUEST = context.global_context_registry.register("linkd.contexts.fastapi.request", RequestContainer)
    """DI context used during HTTP request handling."""


def use_di_context_middleware(app: fastapi.FastAPI, manager: solver.DependencyInjectionManager) -> None:
    """
    Adds middleware to the given fastapi application to handle setting up a DI context for each HTTP request.

    Args:
        app: The fastapi application to add the middleware to.
        manager: The dependency injection manager to use when entering the DI context.

    Returns:
        :obj:`None`

    Example:

        .. code-block:: python

            import fastapi
            import linkd

            app = fastapi.FastAPI()
            linkd.ext.fastapi.use_di_context_middleware(app)
    """
    import fastapi

    @app.middleware("http")
    async def di_context_middleware(  # type: ignore[reportUnusedFunction]
        request: fastapi.Request, call_next: Callable[..., t.Awaitable[fastapi.Response]]
    ) -> fastapi.Response:
        async with manager.enter_context(Contexts.DEFAULT), manager.enter_context(Contexts.REQUEST) as rc:
            rc.add_value(fastapi.Request, request)
            return await call_next(request)


def inject(func: InjectedCallableT) -> InjectedCallableT:
    """
    Specialized decorator enabling linkd-managed dependency injection for fastapi request handlers.

    Linkd-injected parameters MUST be keyword-only, as this decorator rewrites the function signature to
    hide those parameters from fastapi, so that you can still use fastapi dependency injection on non-kw-only
    parameters. See the example for more.

    This parameter MUST be placed below the fastapi route decorator if it is being used.

    Args:
        func: The function to enable DI for.

    Returns:
        The function with dependency injection enabled.

    Warning:
        The standard :meth:`~linkd.solver.inject` decorator WILL NOT work for fastapi request handlers and
        this decorator MUST be used in its place.

    Example:

        .. code-block:: python

            import fastapi
            import linkd

            app = fastapi.FastAPI()
            linkd.ext.fastapi.use_di_context_middleware(app)

            @app.get(...)
            @linkd.ext.fastapi.inject
            async def some_handler(
                # this parameter will be injected by fastapi - path parameter, query parameter, etc.
                foo: str
                # custom fastapi dependencies using 'Depends' are also supported
                bar: Annotated[dict, Depends(some_dependency)],
                *,
                # this parameter will be ignored by fastapi, and injected by linkd instead
                baz: SomeDependency,
            ) -> None:
                ...
    """
    func = solver.inject(func)
    sig = inspect.signature(func)

    new_params: list[inspect.Parameter] = []
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            continue
        new_params.append(param)

    func.__signature__ = sig.replace(parameters=new_params)  # type: ignore[reportMemberAccess]
    return func
