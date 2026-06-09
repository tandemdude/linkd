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
import pytest

import linkd


class TestCompose:
    def test_compose_generates_working_class(self) -> None:
        class Deps(linkd.Compose):
            foo: str
            bar: int

        d = Deps("foo", 1234)
        assert d.foo == "foo"
        assert d.bar == 1234

    def test_compose_preserves_instance_method(self) -> None:
        class Deps(linkd.Compose):
            foo: str
            bar: int

            def joined(self) -> str:
                return f"{self.foo} {self.bar}"

        d = Deps("hello", 42)
        assert d.joined() == "hello 42"

    def test_compose_preserves_classmethod(self) -> None:
        class Deps(linkd.Compose):
            foo: str

            @classmethod
            def cls_name(cls) -> str:
                return cls.__name__

        d = Deps("hi")
        assert d.cls_name() == "Deps"
        assert Deps.cls_name() == "Deps"

    def test_compose_preserves_staticmethod(self) -> None:
        class Deps(linkd.Compose):
            foo: str

            @staticmethod
            def shout(value: str) -> str:
                return value.upper()

        d = Deps("hi")
        assert d.shout("hi") == "HI"
        assert Deps.shout("hi") == "HI"

    def test_compose_preserves_property(self) -> None:
        class Deps(linkd.Compose):
            foo: str

            @property
            def loud(self) -> str:
                return self.foo.upper()

        d = Deps("hi")
        assert d.loud == "HI"

    def test_compose_retains_slots(self) -> None:
        class Deps(linkd.Compose):
            foo: str

        d = Deps("hi")
        assert not hasattr(d, "__dict__")
        with pytest.raises(AttributeError):
            d.extra = "nope"  # type: ignore[attr-defined]


class TestExpose:
    def test_expose_generates_working_class(self) -> None:
        class Deps(linkd.Compose):
            foo: str
            bar: int

        d = Deps("foo", 1234)
        assert d.foo == "foo"
        assert d.bar == 1234

    def test_expose_retains_slots(self) -> None:
        class Deps(linkd.Expose):
            foo: str

        d = Deps("hi")
        assert not hasattr(d, "__dict__")
        with pytest.raises(AttributeError):
            d.extra = "nope"  # type: ignore[attr-defined]

    def test_expose__extract_types_works_for_simple_types(self) -> None:
        class Baz: ...

        class Deps(linkd.Expose):
            foo: str
            bar: int
            baz: Baz

        deps = Deps._extract_types()

        assert len(deps) == 3
        assert deps["foo"] is str
        assert deps["bar"] is int
        assert deps["baz"] is Baz

    def test_expose__extract_types_errors_for_union_types(self) -> None:
        class Deps(linkd.Expose):
            foo: str | int

        with pytest.raises(ValueError):
            Deps._extract_types()

    def test_expose__extract_types_errors_for_condition_types(self) -> None:
        class Deps(linkd.Expose):
            foo: linkd.Try[str]

        with pytest.raises(ValueError):
            Deps._extract_types()

    def test_expose__extract_types_uses_cached_types_for_second_run(self) -> None:
        class Deps(linkd.Expose):
            foo: str

        assert Deps._extract_types() is Deps._extract_types()
