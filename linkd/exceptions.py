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

__all__ = [
    "CircularDependencyException",
    "ContainerClosedException",
    "DependencyInjectionException",
    "DependencyNotSatisfiableException",
    "RegistryFrozenException",
]

import typing as t


class DependencyInjectionException(Exception):
    """Base class for all exceptions raised from the dependency injection system."""


class ContainerClosedException(DependencyInjectionException):
    """Exception raised when attempting to get a dependency from a closed container."""


class CircularDependencyException(DependencyInjectionException):
    """Exception raised when a circular dependency is detected."""


class DependencyNotSatisfiableException(DependencyInjectionException):
    """Exception raised when a dependency is requested but cannot be created."""


class RegistryFrozenException(DependencyInjectionException):
    """Exception raised when attempting to register a new dependency with a frozen registry."""


class CodeGenerationFailedException(DependencyInjectionException, SyntaxError):
    """Exception raised code generation of a dependency resolver function failed."""

    def __init__(self, generated_code: str, exec_globals: dict[str, t.Any]) -> None:
        super().__init__(
            "\n".join(
                [
                    "dependency resolver function generation failed",
                    "generated code was:",
                    "",
                    generated_code,
                    "",
                    f"globals were: {exec_globals}",
                ]
            )
        )
        self.generated_code = generated_code
        self.exec_globals = exec_globals
