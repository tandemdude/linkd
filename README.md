[![PyPI](https://img.shields.io/pypi/v/linkd)](https://pypi.org/project/linkd) [![codecov](https://codecov.io/gh/tandemdude/linkd/graph/badge.svg?token=hZZlq0O9Vx)](https://codecov.io/gh/tandemdude/linkd)

# Overview
Linkd is a powerful [dependency-injection](https://en.wikipedia.org/wiki/Dependency_injection) framework for
asyncio-based Python applications.

This library aims to provide an easy way for framework developers to provide dependency-injection functionality,
while also being suitable for use with standalone applications with a little bit more work.

For an example of `linkd` in action, have a look at [`hikari-lightbulb`](https://github.com/tandemdude/hikari-lightbulb) which
uses it to provide all dependency injection functionality.

## Installation
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install linkd.

```bash
pip install linkd
```

## Usage

### Standalone

The most basic usage of linkd involves three main steps:
- Creating a `DependencyInjectionManager` and registering dependencies
- Setting up an injection context
- Enabling injection on a function

An example of all the above can be seen below:

```python
import asyncio

import linkd

# create a manager instance
manager = linkd.DependencyInjectionManager()
# register a dependency to on of the manager's registries
manager.registry_for(linkd.Contexts.ROOT).register_value(str, "thomm.o")

# enable injection on a function with the inject decorator
@linkd.inject
async def greet(who: str) -> str:
    # the 'who' parameter will be injected by linkd
    return f"hello {who}"


# use the contextual decorator to automatically set up an injection context
@manager.contextual(linkd.Contexts.ROOT)
async def main() -> None:
    # call the injected method
    print(await greet())


if __name__ == "__main__":
    asyncio.run(main())
```

### Supported Framework

Linkd currently supports the following frameworks (click to jump to example usage):
- [FastAPI](https://github.com/tandemdude/linkd/blob/master/examples/fastapi_example.py)
- [Quart](https://github.com/tandemdude/linkd/blob/master/examples/quart_example.py)
- [Starlette](https://github.com/tandemdude/linkd/blob/master/examples/starlette_example.py)

If your framework isn't mentioned here, feel free to open an issue requesting support!

## Issues
If you find any bugs, issues, or unexpected behaviour while using the library,
you should open an issue with details of the problem and how to reproduce if possible.
Please also open an issue for any new features you would like to see added.

## Contributing
Pull requests are welcome. For major changes, please open an issue/discussion first to discuss what you would like to change.

Please try to ensure that documentation is updated if you add any features accessible through the public API.

If you use this library and like it, feel free to sign up to GitHub and star the project,
it is greatly appreciated and lets me know that I'm going in the right direction!

## Links
- **License:** [MIT](https://choosealicense.com/licenses/mit/)
- **Repository:** [GitHub](https://github.com/tandemdude/linkd)
- **Documentation:** [ReadTheDocs](https://linkd.readthedocs.io/en/latest/)
