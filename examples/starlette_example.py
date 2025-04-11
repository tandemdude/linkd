# /// script
# dependencies = [
#   "linkd==0.0.3",
#   "starlette==0.46.1",
#   "uvicorn==0.34.0",
#   "redis==5.2.1",
# ]
# ///
import contextlib
import dataclasses
import json
import typing as t
import uuid

import redis.asyncio as redis_
import uvicorn
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.routing import Route

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


async def user_factory(req: Request, redis: redis_.Redis) -> User:
    user_data = await redis.get(f"user:{req.path_params.get('user_id')}")
    if user_data is None:
        raise RuntimeError("user not found")

    user = User(**json.loads(user_data))
    user._redis = redis
    return user


manager = linkd.DependencyInjectionManager()
manager.registry_for(linkd.ext.starlette.Contexts.DEFAULT).register_value(
    redis_.Redis,
    redis_.Redis.from_url("redis://localhost:6379"),  # type: ignore[reportUnknownMemberType]
    teardown=lambda r: r.aclose(),
)
manager.registry_for(linkd.ext.starlette.Contexts.REQUEST).register_factory(User, user_factory)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette) -> t.AsyncGenerator[None, t.Any]:
    yield
    await manager.close()


@linkd.ext.starlette.inject
async def create_user(req: Request, redis: redis_.Redis) -> Response:
    body = await req.json()

    user = User(id=str(uuid.uuid4()), name=body["name"], email=body["email"])
    user._redis = redis
    await user.save()

    return JSONResponse(user.as_dict())


@linkd.ext.starlette.inject
async def get_or_delete_user(req: Request, user: Try[User] | None) -> Response:
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if req.method == "GET":
        return JSONResponse(user.as_dict())

    await user.delete()
    return Response(status_code=204)


routes = [
    Route("/users/", create_user, methods=["POST"]),
    Route("/users/{user_id}", get_or_delete_user, methods=["GET", "DELETE"]),
]

middleware = [
    Middleware(linkd.ext.starlette.DiContextMiddleware, manager=manager),
]

app = Starlette(routes=routes, lifespan=lifespan, middleware=middleware)
app.state.di = manager


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
