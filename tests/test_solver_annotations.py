from __future__ import annotations

import typing as t

import linkd
from linkd.solver import CANNOT_INJECT
from linkd.solver import _parse_injectable_params

if t.TYPE_CHECKING:
    from linkd import Container


# test that TYPE_CHECKING annotations


class TestTypeCheckingAnnotations:
    def test_annotations_are_parsed_when_in_scope(self) -> None:
        async def m(*, foo: str, bar: linkd.Container) -> None: ...

        pos_or_kw, kw = _parse_injectable_params(m)
        assert len(pos_or_kw) == 0
        assert len(kw) == 2
        assert kw["foo"]._order[0].inner is str  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
        assert kw["bar"]._order[0].inner is linkd.Container  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

    def test_annotations_ignored_when_positional_only_and_not_in_scope(self) -> None:
        async def m(bar: Container, /) -> None: ...

        pos_or_kw, kw = _parse_injectable_params(m)
        assert len(pos_or_kw) == 1
        assert len(kw) == 0
        assert pos_or_kw[0][1] is CANNOT_INJECT
