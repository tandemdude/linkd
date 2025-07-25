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

__all__ = ["Container"]

import logging
import typing as t

from linkd import conditions
from linkd import exceptions
from linkd import graph
from linkd import registry as registry_
from linkd import utils
from linkd.graph import DependencyData

if t.TYPE_CHECKING:
    import types
    from collections.abc import Callable

    from linkd import context

T = t.TypeVar("T")

LOGGER = logging.getLogger(__name__)


class Container:
    """
    A container for managing and supplying dependencies.

    Args:
        registry: The registry of dependencies supply-able by this container.
        parent: The parent container. Defaults to None.
    """

    __slots__ = (
        "_closed",
        "_expression_cache",
        "_graph",
        "_instances",
        "_on_change_listeners",
        "_parent",
        "_registry",
        "_tag",
    )

    def __init__(
        self, registry: registry_.Registry, *, parent: Container | None = None, tag: context.Context | None = None
    ) -> None:
        self._registry = registry
        self._registry._freeze(self)

        self._parent = parent
        self._tag = tag

        self._closed = False

        self._graph: graph.DiGraph = graph.DiGraph(registry._graph)
        self._instances: dict[str, t.Any] = {}

        self._expression_cache: dict[int, t.Any] = {}
        self._on_change_listeners: set[Callable[[], None]] = set()

        self.add_value(Container, self)
        if self._parent is not None:
            self._parent._on_change_listeners.add(self._on_change)

    def __repr__(self) -> str:
        return f"Container(tag={self._tag!r})"

    def __contains__(self, item: t.Any) -> bool:
        if not isinstance(item, str):
            item = utils.get_dependency_id(item)

        if item in self._instances:
            return True

        node = self._graph.nodes.get(item)
        if node is not None:
            return True

        if self._parent is None:
            return False

        return item in self._parent

    async def __aenter__(self) -> Container:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException], exc_val: BaseException, exc_tb: types.TracebackType
    ) -> None:
        await self.close()

    def _on_change(self) -> None:
        self._expression_cache.clear()
        for fn in self._on_change_listeners:
            fn()

    async def close(self) -> None:
        """Closes the container, running teardown procedures for each created dependency belonging to this container."""
        if self._parent is not None:
            self._parent._on_change_listeners.remove(self._on_change)

        for dependency_id, instance in self._instances.items():
            if (node := self._graph.nodes.get(dependency_id)) is None or node.teardown_method is None:
                continue

            await utils.maybe_await(node.teardown_method(instance))

        self._registry._unfreeze(self)
        self._closed = True

    def add_factory(
        self,
        typ: type[T],
        factory: Callable[..., utils.MaybeAwaitable[T]],
        *,
        teardown: Callable[[T], utils.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Adds the given factory as an ephemeral dependency to this container. This dependency is only accessible
        from contexts including this container and will be cleaned up when the container is closed.

        Args:
            typ: The type to register the dependency as.
            factory: The factory used to create the dependency.
            teardown: The teardown function to be called when the container is closed. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        See Also:
            :meth:`linkd.registry.Registry.register_factory` for factory and teardown function spec.
        """
        dependency_id = utils.get_dependency_id(typ)

        if dependency_id in self._graph:
            for edge in self._graph.out_edges(dependency_id):
                self._graph.remove_edge(*edge)

        graph.populate_graph_for_dependency(self._graph, dependency_id, factory, teardown)
        self._on_change()

    def add_value(
        self,
        typ: type[T],
        value: T,
        *,
        teardown: Callable[[T], utils.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Adds the given value as an ephemeral dependency to this container. This dependency is only accessible
        from contexts including this container and will be cleaned up when the container is closed.

        Args:
            typ: The type to register the dependency as.
            value: The value to use for the dependency.
            teardown: The teardown function to be called when the container is closed. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        See Also:
            :meth:`linkd.registry.Registry.register_value` for teardown function spec.
        """
        dependency_id = utils.get_dependency_id(typ)
        self._instances[dependency_id] = value

        if dependency_id in self._graph:
            for edge in self._graph.out_edges(dependency_id):
                self._graph.remove_edge(*edge)

        self._graph.add_node(dependency_id, DependencyData(lambda: None, {}, teardown))
        self._on_change()

    async def _get(self, dependency_id: str) -> t.Any:
        if self._closed:
            raise exceptions.ContainerClosedException("the container is closed")

        # TODO - look into whether locking is necessary - how likely are we to have race conditions
        if (existing := self._instances.get(dependency_id)) is not None:
            return existing

        if (data := self._graph.nodes.get(dependency_id)) is None:
            if self._parent is None:
                raise exceptions.DependencyNotSatisfiableException(
                    f"cannot create dependency {dependency_id!r} - not provided by this or a parent container"
                )

            LOGGER.debug("dependency %r not provided by this container - checking parent", dependency_id)
            return await self._parent._get(dependency_id)

        children = self._graph.children(dependency_id)
        if dependency_id in children:
            raise exceptions.CircularDependencyException(
                f"cannot provide {dependency_id!r} - circular dependency found"
            )

        injectable_params: dict[str, t.Any] = {}
        for param_name, expr in data.factory_params.items():
            LOGGER.debug("evaluating expression %r for factory parameter %r", expr, param_name)
            try:
                injectable_params[param_name] = await expr.resolve(self)
            except exceptions.DependencyNotSatisfiableException as e:
                raise exceptions.DependencyNotSatisfiableException("failed evaluating sub-dependency expression") from e

        try:
            self._instances[dependency_id] = await utils.maybe_await(data.factory_method(**injectable_params))
        except Exception as e:
            raise exceptions.DependencyNotSatisfiableException(
                f"could not create dependency {dependency_id!r} - factory raised exception"
            ) from e

        return self._instances[dependency_id]

    @t.overload
    async def get(self, type_: type[T], /) -> T: ...
    # TODO - TypeExpr
    @t.overload
    async def get(self, type_: t.Any, /) -> t.Any: ...
    async def get(self, type_: t.Any, /) -> t.Any:
        """
        Get a dependency from this container, instantiating it and sub-dependencies if necessary.

        Args:
            type_: The type used when registering the dependency.

        Returns:
            The dependency for the given type.

        Raises:
            :obj:`~linkd.exceptions.ContainerClosedException`: If the container is closed.
            :obj:`~linkd.exceptions.CircularDependencyException`: If the dependency cannot be satisfied
                due to a circular dependency with itself or a sub-dependency.
            :obj:`~linkd.exceptions.DependencyNotSatisfiableException`: If the dependency cannot be satisfied
                for any other reason.
        """
        if self._closed:
            raise exceptions.ContainerClosedException("the container is closed")

        expr = conditions.DependencyExpression.create(type_)
        return await expr.resolve(self)
