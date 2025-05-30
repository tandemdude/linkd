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
import typing as t

import pytest

import linkd


class TestRegistry:
    def test_cannot_register_dependency_that_directly_depends_on_itself(self) -> None:
        registry = linkd.Registry()

        def f(_: object) -> object:
            return object()

        with pytest.raises(linkd.CircularDependencyException):
            registry.register_factory(object, f)

    def test_cannot_add_dependency_when_frozen(self) -> None:
        registry = linkd.Registry()
        registry._freeze(object())  # type: ignore[reportArgumentType]

        with pytest.raises(linkd.RegistryFrozenException):
            registry.register_value(object, object())

    def test_can_add_dependency_when_unfrozen(self) -> None:
        registry = linkd.Registry()

        fake_container = object()
        registry._freeze(fake_container)  # type: ignore[reportArgumentType]
        registry._unfreeze(fake_container)  # type: ignore[reportArgumentType]

        registry.register_value(object, object())

    def test__contains__returns_true_when_dependency_registered(self) -> None:
        registry = linkd.Registry()
        registry.register_value(object, object())
        assert object in registry

    def test__contains__returns_false_when_dependency_not_registered(self) -> None:
        registry = linkd.Registry()
        assert object not in registry

    def test__contains__returns_true_when_NewType_dependency_registered(self) -> None:
        registry = linkd.Registry()
        T = t.NewType("T", object)
        registry.register_value(T, object())
        assert T in registry

    def test__contains__returns_false_when_NewType_dependency_not_registered(self) -> None:
        registry = linkd.Registry()
        T = t.NewType("T", object)
        assert T not in registry

    def test_cannot_have_factory_with_pos_only_args(self) -> None:
        registry = linkd.Registry()

        def f(_: str, /) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    def test_cannot_have_factory_with_var_pos_args(self) -> None:
        registry = linkd.Registry()

        def f(*_: str) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    def test_cannot_have_factory_with_var_kw_args(self) -> None:
        registry = linkd.Registry()

        def f(**_: str) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    def test_cannot_have_factory_with_unannotated_args(self) -> None:
        registry = linkd.Registry()

        def f(_) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)  # type: ignore[reportUnknownArgumentType]

    def test_overriding_dependency_replaces_graph_edges(self) -> None:
        registry = linkd.Registry()

        def f_0(_: str, __: int) -> object:
            return object()

        def f_1(_: float, __: bool) -> object:
            return object()

        registry.register_factory(object, f_0)
        registry.register_factory(object, f_1)
        assert ("object", "str") not in registry._graph.out_edges("object")
