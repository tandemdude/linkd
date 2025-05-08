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


class Deps(linkd.Compose):
    foo: str
    bar: int


class TestBaseCondition:
    def test_cannot_instantiate_with_composite_type(self) -> None:
        with pytest.raises(ValueError):
            linkd.If(int | str)  # type: ignore[reportCallIssue]

    def test_cannot_instantiate_with_composed_type(self) -> None:
        with pytest.raises(ValueError):
            linkd.If(Deps)  # type: ignore[reportCallIssue]

    def test___or___updates_order_correctly(self) -> None:
        cond = (c := linkd.If[str]) | (int | bool)
        assert cond.order == [c, int, bool]  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    def test___ror___updates_order_correctly(self) -> None:
        cond = (int | bool) | (c := linkd.If[str])
        assert cond.order == [int, bool, c]  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

        cond = int | (c := linkd.If[str])
        assert cond.order == [int, c]  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


class TestDependencyExpression:
    def test_cannot_create_from_composed_type(self) -> None:
        with pytest.raises(ValueError):
            linkd.DependencyExpression.create(Deps)

    def test_cannot_create_from_composed_union(self) -> None:
        with pytest.raises(ValueError):
            linkd.DependencyExpression.create(Deps | None)
