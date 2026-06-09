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

__all__ = ["Compose", "Expose"]

import sys
import textwrap
import types
import typing as t

from linkd import conditions
from linkd import utils

if t.TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable

    from typing_extensions import dataclass_transform
else:
    dataclass_transform = lambda: lambda x: x  # noqa: E731


class ComposeMeta(type):
    """Metaclass handling code generation for user-defined :obj:`~Compose` subclasses."""

    @staticmethod
    def _codegen_init(names: Iterable[str]) -> Callable[..., None]:
        joined_names = ",".join(names)
        lines = [
            f"def __init__(self,{joined_names}):",
            *(textwrap.indent(f"self.{n} = {n}", " " * 4) for n in names),
        ]

        exec("\n".join(lines), {}, (generated_locals := {}))
        return t.cast("Callable[..., None]", generated_locals["__init__"])

    def __new__(cls, name: str, bases: tuple[type[t.Any]], attrs: dict[str, t.Any], **kwargs: t.Any) -> type[t.Any]:
        if attrs["__module__"] == "linkd.compose" and (
            attrs["__qualname__"] == "Compose" or attrs["__qualname__"] == "Expose"
        ):
            return super().__new__(cls, name, bases, attrs)

        annotations: dict[str, t.Any]
        if "__annotations__" in attrs:
            annotations = attrs["__annotations__"]
        elif (func := attrs.get("__annotate__")) or (func := attrs.get("__annotate_func__")):
            import annotationlib

            annotations = annotationlib.call_annotate_function(func, annotationlib.Format.VALUE)
        else:
            name = "Compose" if Compose in bases else "Expose"
            raise RuntimeError(f"Could not resolve annotations for {name} subclass")

        attrs["__slots__"] = tuple(annotations)
        attrs["__init__"] = cls._codegen_init(annotations)
        attrs[utils._COMPOSE_MARKER_ATTR if Compose in bases else utils._EXPOSE_MARKER_ATTR] = True
        return super().__new__(cls, name, bases, attrs)


@dataclass_transform()
class Compose(metaclass=ComposeMeta):
    """
    Class allowing for "composing" of multiple dependencies into a single object, to help declutter
    the signatures of functions that require a large number of dependencies.

    If you have ever used msgspec or pydantic this will feel familiar. To use this feature, simply create a
    subclass of this class and define fields for the dependencies you wish to use.

    .. code-block:: python

        class ComposedDependencies(linkd.Compose):
            foo: FooDep
            bar: BarDep
            baz: BazDep

    Then, in place of specifying ``foo``, ``bar`` and ``baz`` within the function signature, you can request
    a single object of type ``ComposedDependencies``.

    .. code-block:: python

        async def function(deps: ComposedDependencies):
            ...

    Linkd will automatically try to create an instance of your composed class with all the dependencies that
    it requires. As with defining dependencies within the function signature, you can use fallback and ``If`` or ``Try``
    syntax within the composed class field annotations.

    Methods, classmethods, staticmethods and properties defined on the subclass are preserved and accessible
    on instances as normal.

    .. warning::
        None of the fields may contain a dependency on a composed class.
    """

    __slots__ = ()


@dataclass_transform()
class Expose(metaclass=ComposeMeta):
    __slots__ = ()

    @classmethod
    def _extract_types(cls) -> dict[str, t.Any]:
        if hasattr(cls, utils._DEPS_ATTR):
            return getattr(cls, utils._DEPS_ATTR)

        # introspect and store attrs on class on instantiation
        hints = t.get_type_hints(cls, localns={m: sys.modules[m] for m in utils.ANNOTATION_PARSE_LOCAL_INCLUDE_MODULES})
        deps = {name: annotation for name, annotation in hints.items() if name in getattr(cls, "__slots__")}

        # ensure annotations are valid; 'Expose' classes may not use presence conditions, nor contain
        # a union other than 'type | None'. Each attribute must map to exactly one type.
        for name, dep in deps.items():
            if t.get_origin(dep) in (types.UnionType, t.Union):
                raise ValueError(f"'{cls.__name__}.{name}': unions are not permitted as 'Expose' dependencies")

            if isinstance(dep, conditions.BaseCondition):
                raise ValueError(f"'{cls.__name__}.{name}': conditions are not permitted as 'Expose' dependencies")

        setattr(cls, utils._DEPS_ATTR, deps)
        return deps
