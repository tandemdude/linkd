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

__all__ = ["Context", "ContextRegistry", "Contexts", "DefaultContainer", "global_context_registry"]

import typing as t

from linkd import container

Context = t.NewType("Context", str)
"""
Type representing a dependency injection context. Used for labelling containers so that they
can be accessed using method injection if required. You can create and use your own contexts by
creating an instance of this type.
"""

DefaultContainer = t.NewType("DefaultContainer", container.Container)
"""Injectable type representing the dependency container for the default context."""


class ContextRegistry:
    __slots__ = ("_contexts",)

    def __init__(self) -> None:
        self._contexts: dict[Context, type[container.Container] | None] = {}

    def register(self, ns: str, linked_type: type[container.Container] | None = None) -> Context:
        self._contexts[c := Context(ns)] = linked_type
        return c

    def unregister(self, context: Context) -> None:
        del self._contexts[context]

    def type_for(self, context: Context) -> type[container.Container] | None:
        if context in self._contexts:
            return self._contexts[context]
        # TODO - maybe error that context has not been registered?
        return None


global_context_registry: ContextRegistry = ContextRegistry()


@t.final
class Contexts:
    """Collection of the dependency injection context values linkd uses."""

    __slots__ = ()

    DEFAULT = global_context_registry.register("linkd.contexts.default", DefaultContainer)
    """The base DI context - ALL other contexts are built with this as the parent."""
