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
"""A powerful async-only dependency injection framework for Python."""

from linkd import ext
from linkd.conditions import *
from linkd.container import *
from linkd.context import *
from linkd.exceptions import *
from linkd.graph import *
from linkd.registry import *
from linkd.solver import *

__all__ = [
    "DI_CONTAINER",
    "DI_ENABLED",
    "INJECTED",
    "AutoInjecting",
    "CircularDependencyException",
    "Container",
    "ContainerClosedException",
    "Context",
    "ContextRegistry",
    "Contexts",
    "DependencyData",
    "DependencyExpression",
    "DependencyInjectionException",
    "DependencyInjectionManager",
    "DependencyNotSatisfiableException",
    "DiGraph",
    "If",
    "Registry",
    "RegistryFrozenException",
    "RootContainer",
    "Try",
    "ext",
    "global_context_registry",
    "inject",
]

# Do not change the below field manually. It is updated by CI upon release.
__version__ = "0.0.4"
