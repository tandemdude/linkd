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

__all__ = ["DI_CONTAINER", "DI_ENABLED", "INJECTED", "AutoInjecting", "DependencyInjectionManager", "inject"]

import collections
import contextlib
import contextvars
import functools
import inspect
import logging
import os
import sys
import typing as t
from collections.abc import Coroutine

from linkd import conditions
from linkd import container
from linkd import context as context_
from linkd import exceptions
from linkd import registry
from linkd import utils

if t.TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from collections.abc import Awaitable
    from collections.abc import Callable

P = t.ParamSpec("P")
R = t.TypeVar("R")
T = t.TypeVar("T")
AsyncFnT = t.TypeVar("AsyncFnT", bound=t.Callable[..., Coroutine[t.Any, t.Any, t.Any]])

DI_ENABLED: t.Final[bool] = os.environ.get("LINKD_DI_DISABLED", "false").lower() != "true"
DI_CONTAINER: contextvars.ContextVar[container.Container | None] = contextvars.ContextVar(
    "linkd_container", default=None
)
LOGGER = logging.getLogger(__name__)

INJECTED: t.Final[t.Any] = utils.Marker("INJECTED")
"""
Flag value used to explicitly mark that a function parameter should be dependency-injected.

This exists to stop type checkers complaining that function arguments are not provided when calling
dependency-injection enabled functions.

Example:

    .. code-block:: python

        @linkd.inject
        async def foo(bar: SomeClass = linkd.INJECTED) -> None:
            ...

        # Type-checker shouldn't error that a parameter is missing
        await foo()
"""


class _NoOpContainer(container.Container):
    __slots__ = ()

    def add_factory(
        self,
        typ: type[T],
        factory: Callable[..., utils.MaybeAwaitable[T]],
        *,
        teardown: Callable[[T], utils.MaybeAwaitable[None]] | None = None,
    ) -> None: ...

    def add_value(
        self,
        typ: type[T],
        value: T,
        *,
        teardown: Callable[[T], utils.MaybeAwaitable[None]] | None = None,
    ) -> None: ...

    def _get(self, dependency_id: str) -> t.Any:
        raise exceptions.DependencyNotSatisfiableException("dependency injection is globally disabled")


_NOOP_CONTAINER = _NoOpContainer(registry.Registry(), tag=context_.Contexts.ROOT)


class DependencyInjectionManager:
    """Class which contains dependency injection functionality."""

    __slots__ = ("_default_container", "_registries")

    def __init__(self) -> None:
        self._registries: dict[context_.Context, registry.Registry] = collections.defaultdict(registry.Registry)
        self._default_container: container.Container | None = None

    @property
    def default_container(self) -> container.Container | None:
        """
        The container being used to provide dependencies for the :attr:`~Contexts.ROOT` context. This will
        be :obj:`None` until the first time any injection context is entered.
        """
        return self._default_container

    def registry_for(self, context: context_.Context, /) -> registry.Registry:
        """
        Get the dependency registry for the given context. Creates one if necessary.

        Args:
            context: The injection context to get the registry for.

        Returns:
            The dependency registry for the given context.
        """
        return self._registries[context]

    @contextlib.asynccontextmanager
    async def enter_context(
        self, context: context_.Context = context_.Contexts.ROOT, /
    ) -> AsyncIterator[container.Container]:
        """
        Context manager that ensures a dependency injection context is available for the nested operations.

        Args:
            context: The context to enter. If a container for the given context already exists, it will be returned
                and a new container will not be created.

        Yields:
            :obj:`~linkd.container.Container`: The container that has been entered.

        Example:

            .. code-block:: python

                # Enter a specific context ('manager' is your DependencyInjectionManager instance)
                async with manager.enter_context(linkd.Contexts.ROOT):
                    await some_function_that_needs_dependencies()

        Note:
            If you want to enter multiple contexts - i.e. a command context that requires the default context to
            be available first - you should call this once for each context that is needed.

            .. code-block:: python

                async with (
                    manager.enter_context(linkd.Contexts.ROOT),
                    manager.enter_context(SOME_COMMAND_CONTEXT)
                ):
                    ...
        """
        if not DI_ENABLED:
            # Return a container that will never register dependencies and cannot have dependencies
            # retrieved from it - it will always raise an error if someone tries to use DI while it is
            # globally disabled.
            yield _NOOP_CONTAINER
            return

        LOGGER.debug("attempting to enter context %r", context)

        new_container: container.Container | None = None
        created: bool = False

        token, value = None, DI_CONTAINER.get(None)
        if value is not None:
            LOGGER.debug("searching for existing container for context %r", context)
            this = value
            while this:
                if this._tag == context:
                    new_container = this
                    LOGGER.debug("existing container found for context %r", context)
                    break

                this = this._parent

        if new_container is None:
            if context == context_.Contexts.ROOT and self._default_container is not None:
                LOGGER.debug("reusing existing container for context %r", context)
                new_container = self._default_container
            else:
                LOGGER.debug("creating new container for context %r", context)

                new_container = container.Container(self._registries[context], parent=value, tag=context)
                if (cls := context_.global_context_registry.type_for(context)) is not None:
                    new_container.add_value(cls, new_container)

                if context == context_.Contexts.ROOT:
                    new_container.add_value(DependencyInjectionManager, self)
                    self._default_container = new_container

                created = True

        token = DI_CONTAINER.set(new_container)
        LOGGER.debug("entered context %r", context)

        try:
            if new_container is self._default_container or not created:
                yield new_container
            else:
                async with new_container:
                    yield new_container
        finally:
            DI_CONTAINER.reset(token)
            LOGGER.debug("cleared context %r", context)

    def contextual(self, context: context_.Context, /, *contexts: context_.Context) -> Callable[[AsyncFnT], AsyncFnT]:
        """
        Convenience decorator that enters the given DI context(s) for the decorated function. The requested contexts
        will be entered **IN ORDER**, and so in most cases the first one should be :obj:`~linkd.context.Contexts.ROOT`.

        Args:
            context: The first context to enter.
            *contexts: Additional contexts to enter.

        Note:
            If a context would already be available and this decorator is used, the contexts will be **reapplied**.
            For example, if you are in a request handler with the `REQUEST` context enabled, and a function decorated
            with this - `@manager.contextual(Contexts.ROOT, Contexts.REQUEST)` - is called, the `REQUEST` context
            will be re-entered and will not have access to any of the dependencies already instantiated in the
            previous instance of the context.

        Example:

            .. code-block:: python

                manager = linkd.DependencyInjectionManager()

                ...

                @manager.contextual(Contexts.ROOT, Contexts.REQUEST)
                @linkd.injected
                async def foo(bar: Bar) -> Baz:
                    ...
        """
        resolved_contexts = [context, *contexts]

        def inner(func: AsyncFnT) -> AsyncFnT:
            @functools.wraps(func)
            async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
                async with contextlib.AsyncExitStack() as stack:
                    for ctx in resolved_contexts:
                        await stack.enter_async_context(self.enter_context(ctx))

                    return await func(*args, **kwargs)

            return t.cast("AsyncFnT", wrapper)

        return inner

    async def close(self) -> None:
        """
        Close the default dependency injection context. This **must** be called if you wish the teardown
        functions for any dependencies registered for the default registry to be called.

        Returns:
            :obj:`None`
        """
        if self._default_container is not None:
            await self._default_container.close()
            self._default_container = None


CANNOT_INJECT: t.Final[t.Any] = utils.Marker("CANNOT_INJECT")


def _parse_injectable_params(func: Callable[..., t.Any]) -> tuple[list[tuple[str, t.Any]], dict[str, t.Any]]:
    positional_or_keyword_params: list[tuple[str, t.Any]] = []
    keyword_only_params: dict[str, t.Any] = {}

    parameters = inspect.signature(
        func, locals={m: sys.modules[m] for m in utils.ANNOTATION_PARSE_LOCAL_INCLUDE_MODULES}, eval_str=True
    ).parameters
    for parameter in parameters.values():
        if (
            # If the parameter has no annotation
            parameter.annotation is inspect.Parameter.empty
            # If the parameter is not positional-or-keyword or keyword-only
            or parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            # If it has a default that isn't INJECTED
            or ((default := parameter.default) is not inspect.Parameter.empty and default is not INJECTED)
        ):
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                positional_or_keyword_params.append((parameter.name, CANNOT_INJECT))
            continue

        expr = conditions.DependencyExpression.create(parameter.annotation)
        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
            positional_or_keyword_params.append((parameter.name, expr))
        else:
            # It has to be a keyword-only parameter
            keyword_only_params[parameter.name] = expr

    return positional_or_keyword_params, keyword_only_params


class AutoInjecting:
    """
    Wrapper for a callable that implements dependency injection. When called, resolves the required
    dependencies and calls the original callable. Supports both synchronous and asynchronous functions,
    however this cannot be called synchronously - synchronous functions will need to be awaited.

    You should generally never have to instantiate this yourself - you should instead use one of the
    decorators that applies this to the target automatically.

    See Also:
        :meth:`~inject`
    """

    __slots__ = ("_func", "_kw_only_params", "_pos_or_kw_params", "_self")

    def __init__(
        self,
        func: Callable[..., Awaitable[t.Any]],
        self_: t.Any = None,
        _cached_pos_or_kw_params: list[tuple[str, t.Any]] | None = None,
        _cached_kw_only_params: dict[str, t.Any] | None = None,
    ) -> None:
        self._func = func
        self._self: t.Any = self_

        if _cached_pos_or_kw_params is not None and _cached_kw_only_params is not None:
            self._pos_or_kw_params = _cached_pos_or_kw_params
            self._kw_only_params = _cached_kw_only_params
        else:
            self._pos_or_kw_params, self._kw_only_params = _parse_injectable_params(func)

    def __get__(self, instance: t.Any, _: type[t.Any]) -> AutoInjecting:
        if instance is not None:
            return AutoInjecting(self._func, instance, self._pos_or_kw_params, self._kw_only_params)
        return self

    def __getattr__(self, item: str) -> t.Any:
        return getattr(self._func, item)

    def __setattr__(self, key: str, value: t.Any) -> None:
        if key in self.__slots__:
            return super().__setattr__(key, value)

        setattr(self._func, key, value)

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        new_kwargs: dict[str, t.Any] = {}
        new_kwargs.update(kwargs)

        di_container: container.Container | None = DI_CONTAINER.get(None)

        injectables = {
            name: type
            for name, type in self._pos_or_kw_params[len(args) + (self._self is not None) :]
            if name not in new_kwargs
        }
        injectables.update({name: type for name, type in self._kw_only_params.items() if name not in new_kwargs})

        for name, type_expr in injectables.items():
            # Skip any arguments that we can't inject
            if type_expr is CANNOT_INJECT:
                continue

            if di_container is None:
                raise exceptions.DependencyNotSatisfiableException("no DI context is available")

            assert isinstance(type_expr, conditions.DependencyExpression)

            LOGGER.debug("requesting dependency matching %r", type_expr)  # type: ignore[reportUnknownArgumentType]
            new_kwargs[name] = await type_expr.resolve(di_container)

        if len(new_kwargs) > len(kwargs):
            func_name = ((self._self.__class__.__name__ + ".") if self._self else "") + self._func.__name__
            LOGGER.debug("calling function %r with resolved dependencies", func_name)

        if self._self is not None:
            return await utils.maybe_await(self._func(self._self, *args, **new_kwargs))
        return await utils.maybe_await(self._func(*args, **new_kwargs))


@t.overload
def inject(func: AsyncFnT) -> AsyncFnT: ...
@t.overload
def inject(func: Callable[P, R]) -> Callable[P, Coroutine[t.Any, t.Any, R]]: ...
def inject(func: Callable[P, utils.MaybeAwaitable[R]]) -> Callable[P, Coroutine[t.Any, t.Any, R]]:
    """
    Decorator that enables dependency injection on the decorated function. If dependency injection
    has been disabled globally then this function does nothing and simply returns the object that was passed in.

    Args:
        func: The function to enable dependency injection for.

    Returns:
        The function with dependency injection enabled, or the same function if DI has been disabled globally.

    Warning:
        Dependency injection relies on a context being available when the function is called.
        Refer to library documentation for which flows will have a dependency injection context set-up
        for you automatically. Otherwise, you will have to set up the context yourself using the helper
        context manager :meth:`~DependencyInjectionManager.enter_context`.
    """
    if DI_ENABLED and not isinstance(func, AutoInjecting):
        return AutoInjecting(func)  # type: ignore[reportReturnType]
    return func  # type: ignore[reportReturnType]
