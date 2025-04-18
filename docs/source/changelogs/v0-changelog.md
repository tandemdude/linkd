<!-- This file is automatically generated. Do not edit manually. -->
(v0-changelog)=
# Version 0 Changelog

Below are all the changelogs for versions of `linkd` since `0.0.0`.

----

<!-- next-changelog -->

## v0.0.4 (2025-04-13)
### Breaking Changes

- Renamed `linkd.Contexts.DEFAULT` to `linkd.Contexts.ROOT` for clarity.

### Features

- Add support for Starlette applications through the `linkd.ext.starlette` submodule. ([#5](https://github.com/tandemdude/linkd/issues/5))
- Add support for Quart applications through the `linkd.ext.quart` submodule. ([#6](https://github.com/tandemdude/linkd/issues/6))
- Added convenience `DependencyInjectionManager.contextual` decorator to allow easily entering a DI context as a one-off.

----

## v0.0.3 (2025-04-10)
### Features

- Add support for FastAPI applications through the `linkd.ext.fastapi` submodule. ([#1](https://github.com/tandemdude/linkd/issues/1))

----

## v0.0.2 (2025-04-08)
### Breaking Changes

- Renamed `with_di` decorator to `inject` - use `@linkd.inject` instead of `@linkd.with_di`.

----

## v0.0.1 (2025-04-08)

- Initial release. No changes to see here!
