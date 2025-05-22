from asyncio import run
from cashews import cache
from os import getenv, environ

from discord.utils import setup_logging
from contextlib import suppress

from vesta.framework import Vesta

cache.setup(getenv("REDIS_URL", "redis://localhost:6379"))
# cache.setup("mem://")

environ["JISHAKU_NO_UNDERSCORE"] = "True"
environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
environ["JISHAKU_HIDE"] = "True"
environ["JISHAKU_FORCE_PAGINATOR"] = "True"
environ["JISHAKU_RETAIN"] = "True"


async def startup() -> None:
    with suppress(KeyboardInterrupt):
        async with Vesta() as bot:
            setup_logging()
            await bot.start()


if __name__ == "__main__":
    run(startup())
