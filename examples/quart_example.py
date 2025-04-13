# /// script
# dependencies = [
#   "linkd>=0.0.4",
#   "quart==0.20.0",
#   "uvicorn==0.34.0",
#   "redis==5.2.1",
# ]
# ///
import dataclasses
import json
import typing as t
import uuid

import quart
import redis.asyncio as redis_
import uvicorn

import linkd
from linkd import Try


@dataclasses.dataclass
class User:
    id: str
    name: str
    email: str

    _redis: redis_.Redis = dataclasses.field(init=False, repr=False)

    def as_dict(self) -> dict[str, t.Any]:
        return {"id": self.id, "name": self.name, "email": self.email}

    async def save(self) -> None:
        await self._redis.set(f"user:{self.id}", json.dumps(self.as_dict()))

    async def delete(self) -> None:
        await self._redis.delete(f"user:{self.id}")


async def user_factory(redis: redis_.Redis) -> User:
    user_id = quart.request.path.split("/")[-1]

    user_data = await redis.get(f"user:{user_id}")
    if user_data is None:
        raise RuntimeError("user not found")

    user = User(**json.loads(user_data))
    user._redis = redis
    return user


manager = linkd.DependencyInjectionManager()
manager.registry_for(linkd.ext.starlette.Contexts.ROOT).register_value(
    redis_.Redis,
    redis_.Redis.from_url("redis://localhost:6379"),  # type: ignore[reportUnknownMemberType]
    teardown=lambda r: r.aclose(),
)
manager.registry_for(linkd.ext.starlette.Contexts.REQUEST).register_factory(User, user_factory)

app = quart.Quart(__name__)
app.asgi_app = linkd.ext.quart.DiContextMiddleware(app.asgi_app, manager)


@app.after_serving
async def shutdown() -> None:
    await manager.close()


@app.route("/users/", methods=["POST"])
@linkd.inject
async def create_user(redis: redis_.Redis) -> quart.Response:
    body = await quart.request.json

    user = User(id=str(uuid.uuid4()), name=body["name"], email=body["email"])
    user._redis = redis
    await user.save()

    return quart.jsonify(user.as_dict())


# Quart requires route handlers to take and URL parameters as keyword arguments, so unfortunately
# the unused parameter needs to be included in the below route handlers.


@app.route("/users/<user_id>", methods=["GET"])
@linkd.inject
async def get_user(user_id: str, user: Try[User] | None) -> quart.Response:  # noqa: RUF029
    if user is None:
        return quart.Response(status=404)

    return quart.jsonify(user.as_dict())


@app.route("/users/<user_id>", methods=["DELETE"])
@linkd.inject
async def delete_user(user_id: str, user: Try[User] | None) -> quart.Response:
    if user is None:
        return quart.Response(status=404)

    await user.delete()
    return quart.Response(status=204)


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
