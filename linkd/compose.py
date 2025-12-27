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

__all__ = ["Compose"]

import inspect
import textwrap
import typing as t

if t.TYPE_CHECKING:
    import typing_extensions as t_ex
    from typing_extensions import dataclass_transform
else:
    dataclass_transform = lambda: lambda x: x  # noqa: E731

_ACTUAL_ATTR: t.Final[str] = "__linkd_actual__"
_DEPS_ATTR: t.Final[str] = "__linkd_deps__"


def _is_compose_class(item: t.Any) -> t_ex.TypeIs[type[Compose]]:  # type: ignore[reportUnusedFunction]
    return hasattr(item, _ACTUAL_ATTR) and inspect.isclass(item)


class ComposeMeta(type):
    """Metaclass handling code generation for user-defined :obj:`~Compose` subclasses."""

    @staticmethod
    def _codegen_compose_cls(name: str, attrs: dict[str, t.Any]) -> type[t.Any]:
        joined_names = ",".join(attrs)
        joined_quoted_names = ",".join(f'"{n}"' for n in attrs) + ("," if len(attrs) == 1 else "")

        lines = [
            f"class {name}:",
            f"    __slots__ = ({joined_quoted_names})",
            f"    def __init__(self,{joined_names}):",
            *(textwrap.indent(f"self.{n} = {n}", " " * 8) for n in attrs),
        ]

        exec("\n".join(lines), {}, (generated_locals := {}))
        return t.cast("type[t.Any]", generated_locals[name])

    def __new__(cls, name: str, bases: tuple[type[t.Any]], attrs: dict[str, t.Any], **kwargs: t.Any) -> type[t.Any]:
        if attrs["__module__"] == "linkd.compose" and attrs["__qualname__"] == "Compose":
            return super().__new__(cls, name, bases, attrs)

        annotations: dict[str, t.Any]
        if "__annotations__" in attrs:
            annotations = attrs["__annotations__"]
        elif "__annotate__" in attrs:
            import annotationlib

            annotations = annotationlib.call_annotate_function(attrs["__annotate__"], annotationlib.Format.VALUE)
        else:
            raise RuntimeError("Could not resolve annotations for Compose subclass")

        generated = cls._codegen_compose_cls(name, annotations)
        setattr(generated, _ACTUAL_ATTR, super().__new__(cls, name, bases, attrs))

        return generated


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
    it requires. As with defining dependencies within the function signature, you can use fallback and `If` or `Try`
    syntax within the composed class field annotations.

    .. warning::
        None of the fields may contain a dependency on a composed class.

    .. warning::
        Composed classes cannot have any defined methods, they will be erased at runtime.
    """

    __slots__ = ()
