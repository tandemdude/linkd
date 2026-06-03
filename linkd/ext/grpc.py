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
"""
Extension module adding support for using linkd-based dependency injection with `gRPC <https://grpc.io/>`_.

See the examples directory for a full working application using this module.

.. note::
    Unlike the ``FastAPI`` and ``Starlette`` integrations, the default :meth:`~linkd.solver.inject` method
    will work for method handlers when using this extension.

----
"""

from __future__ import annotations

__all__ = ["Contexts", "DiInterceptor"]

import functools
import sys
import typing as t

if t.TYPE_CHECKING:
    from linkd.ext._grpc import Contexts as Contexts
    from linkd.ext._grpc import DiInterceptor as DiInterceptor
else:
    try:
        from linkd.ext._grpc import Contexts
        from linkd.ext._grpc import DiInterceptor
    except ImportError:

        class __LazyLoader:
            def __init__(self) -> None:
                self.module = sys.modules[__name__]

            def __getattr__(self, name: str) -> t.Any:
                return getattr(self.module, name)

            @functools.cached_property
            def Contexts(self) -> type[Contexts]:  # noqa: N802
                from linkd.ext._grpc import Contexts

                return Contexts

            @functools.cached_property
            def DiInterceptor(self) -> type[DiInterceptor]:  # noqa: N802
                from linkd.ext._grpc import DiInterceptor

                return DiInterceptor

        sys.modules[__name__] = __LazyLoader()
