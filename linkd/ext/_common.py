# api_ref_gen::ignore
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

__all__ = ["REQUEST_CONTEXT", "InjectedCallableT", "RequestContainer"]

import functools
import inspect
import typing as t
from collections.abc import Callable

from linkd import container
from linkd import context
from linkd import solver

InjectedCallableT = t.TypeVar("InjectedCallableT", bound=Callable[..., t.Any])

RequestContainer = t.NewType("RequestContainer", container.Container)
"""Injectable type representing the dependency container for the HTTP request context."""

REQUEST_CONTEXT = context.global_context_registry.register("linkd.contexts.http.request", RequestContainer)


def enable_injection_kw_erased(func: InjectedCallableT) -> InjectedCallableT:
    injection_enabled = solver.inject(func)

    sig = inspect.signature(func)
    new_params: list[inspect.Parameter] = []
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            continue
        new_params.append(param)

    @functools.wraps(func)
    async def _wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        return await injection_enabled(*args, **kwargs)

    _wrapper.__signature__ = sig.replace(parameters=new_params)  # type: ignore[reportMemberAccess]
    return t.cast("InjectedCallableT", _wrapper)
