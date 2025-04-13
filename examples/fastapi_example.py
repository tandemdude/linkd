# /// script
# dependencies = [
#   "linkd>=0.0.4",
#   "fastapi[standard]==0.115.12",
#   "redis==5.2.1",
# ]
# ///
import contextlib
import typing as t
import uuid

import fastapi
import pydantic
import redis.asyncio as redis_
import uvicorn

import linkd
from linkd import Try


class User(pydantic.BaseModel):
    id: str
    name: str
    email: str

    _redis: redis_.Redis

    async def save(self) -> None:
        await self._redis.set(f"user:{self.id}", self.model_dump_json())

    async def delete(self) -> None:
        await self._redis.delete(f"user:{self.id}")


async def user_factory(req: fastapi.Request, redis: redis_.Redis) -> User:
    user_data = await redis.get(f"user:{req.path_params.get('user_id')}")
    if user_data is None:
        raise RuntimeError("user not found")

    user = User.model_validate_json(user_data)
    user._redis = redis
    return user


manager = linkd.DependencyInjectionManager()
manager.registry_for(linkd.ext.fastapi.Contexts.ROOT).register_value(
    redis_.Redis,
    redis_.Redis.from_url("redis://localhost:6379"),  # type: ignore[reportUnknownMemberType]
    teardown=lambda r: r.aclose(),
)
manager.registry_for(linkd.ext.fastapi.Contexts.REQUEST).register_factory(User, user_factory)


@contextlib.asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> t.AsyncGenerator[None, t.Any]:
    yield
    await manager.close()


app = fastapi.FastAPI(lifespan=lifespan)
app.state.di = manager
linkd.ext.fastapi.use_di_context_middleware(app, manager)


class UserCreateBody(pydantic.BaseModel):
    name: str
    email: str


@app.post("/users/")
@linkd.ext.fastapi.inject
async def create_user(body: UserCreateBody, *, redis: redis_.Redis) -> User:
    user = User(id=str(uuid.uuid4()), name=body.name, email=body.email)  # type: ignore[reportCallIssue]
    user._redis = redis
    await user.save()

    return user


@app.get("/users/{user_id}")
@linkd.ext.fastapi.inject
async def get_user(*, user: Try[User] | None) -> User:
    if user is None:
        raise fastapi.HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/users/{user_id}", status_code=204)
@linkd.ext.fastapi.inject
async def delete_user(*, user: Try[User] | None) -> None:
    if user is None:
        raise fastapi.HTTPException(status_code=404, detail="User not found")
    await user.delete()


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
