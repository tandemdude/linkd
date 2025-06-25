# /// script
# dependencies = [
#   "linkd",
# ]
# ///
import asyncio

import linkd


class Greeter:
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"Hello {self.name}"


manager = linkd.DependencyInjectionManager()
manager.registry_for(linkd.Contexts.ROOT).register_factory(Greeter, lambda: Greeter("linkd-testing"))


@linkd.inject
def print_greeting(greeter: Greeter = linkd.INJECTED) -> None:
    print(greeter.greet())


@manager.contextual(linkd.Contexts.ROOT)
async def main() -> None:
    await print_greeting()


if __name__ == "__main__":
    asyncio.run(main())
