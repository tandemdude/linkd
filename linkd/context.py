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

__all__ = ["Context", "ContextRegistry", "Contexts", "RootContainer", "global_context_registry"]

import typing as t

from linkd import container

Context = t.NewType("Context", str)
"""
Type representing a dependency injection context. Used for labelling containers so that they
can be accessed using method injection if required. You can create and use your own contexts by
creating an instance of this type.
"""

RootContainer = t.NewType("RootContainer", container.Container)
"""Injectable type representing the dependency container for the root context."""


class ContextRegistry:
    """
    A registry for all DI contexts known to linkd. This acts as a mapping of a context to the
    type that the container will register itself as when one is created for that context, allowing
    accessing a specific context's container from anywhere within a nested DI flow.

    It is not absolutely necessary to register a context to a registry in order to use it, however
    it is required if you want to provide a custom injectable type for that container automatically.
    """

    __slots__ = ("_contexts",)

    def __init__(self) -> None:
        self._contexts: dict[Context, type[container.Container] | None] = {}

    def register(self, ns: str, linked_type: type[container.Container] | None = None) -> Context:
        """
        Create and register a DI context to this registry, along with an optional injectable type.

        Args:
            ns: The namespace for the new context. This should be an identifier unique to your library/application.
                For example, linkd uses the root namespace ``linkd.contexts.<...extras>`` for its included contexts.
            linked_type: The injectable container type for this context. Defaults to :obj:`None`.

        Returns:
            The created context.

        Raises:
            :obj:`KeyError`: If a context using the same identifier already exists.

        Example:

            .. code-block:: python

                class YourContexts:
                    DEFAULT = linkd.Contexts.DEFAULT
                    FOO = linkd.global_context_registry.register("com.example.contexts.foo")
        """
        if ns in self._contexts:
            raise KeyError("A context with name '{}' already exists".format(ns))

        self._contexts[c := Context(ns)] = linked_type
        return c

    def unregister(self, context: Context) -> None:
        """
        Unregister a DI context from this registry.

        Args:
            context: The context to unregister.

        Returns:
            :obj:`None`

        Raises:
            :obj:`KeyError`: If the context had not previously been registered.
        """
        del self._contexts[context]

    def type_for(self, context: Context) -> type[container.Container] | None:
        """
        Get the stored type for the given context. This function is used internally when containers are created.

        Args:
            context: The context to get the type for.

        Returns:
            The stored type for the given context, or :obj:`None` if no type was stored, or the
            context was not registered.
        """
        if context in self._contexts:
            return self._contexts[context]
        return None


global_context_registry: ContextRegistry = ContextRegistry()
"""The global context registry."""


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd uses."""

    __slots__ = ()

    ROOT = global_context_registry.register("linkd.contexts.default", RootContainer)
    """The root DI context - ALL other contexts are built with this as the parent."""
