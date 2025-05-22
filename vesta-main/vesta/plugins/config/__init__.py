from discord.ext.commands import Cog

from vesta.framework import Vesta

from .alias import Alias
from .backup import Backup
from .boosterrole import BoosterRole
from .command import CommandManagement
from .disboard import Disboard
from .gallery import Gallery
# from .invoke import Invoke - rewriting from scratch
# from .level import Level
from .logging import Logging
from .pingonjoin import PingOnJoin
# from .prefix import Prefix
from .publisher import Publisher
from .roles import Roles
from .security import AntiNuke, AntiRaid
from .starboard import Starboard
from .statistics import Statistics
from .sticky import Sticky
# from .system import System
from .tags import Tags
from .thread import Thread
from .timer import Timer
from .trigger import Trigger
from .voicemaster import VoiceMaster
from .webhook import Webhook
from .whitelist import Whitelist

class Config(
    Alias,
    AntiNuke,
    AntiRaid,
    Backup,
    BoosterRole,
  #  CommandManagement,
    Disboard,
    Gallery,
    Logging,
    Publisher,
    PingOnJoin,
    Roles,
    Starboard,
    Statistics,
    Sticky,
    Tags,
    Timer,
    Thread,
    Trigger,
    VoiceMaster,
    Webhook,
    Whitelist,
    Cog,
):
    """
    Load all the configuration cogs into one cog.
    """
    def __init__(self, bot: Vesta):
        self.bot = bot


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Config(bot))
