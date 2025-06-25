(quickstart)=
# Quickstart

Linkd can be installed using pip:
:::{prompt}
:language: bash

pip install linkd
:::

:::{important}
You must have Python 3.10 or higher in order to use linkd.
:::

## Standalone

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

## Supported Framework

Linkd currently supports the following frameworks (click to jump to example usage):
- [FastAPI](https://github.com/tandemdude/linkd/blob/master/examples/fastapi_example.py)
- [Quart](https://github.com/tandemdude/linkd/blob/master/examples/quart_example.py)
- [Starlette](https://github.com/tandemdude/linkd/blob/master/examples/starlette_example.py)

If your framework isn't mentioned here, feel free to open an issue requesting support!
