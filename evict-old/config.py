
class DISCORD:
    """
    Main bot connection class.
    """
    TOKEN: str = (
        "MTIwMzUxNDY4NDMyNjgwNTUyNA.GBtNR0.9kai-teBcdbvsP2lWn0_hhP1IKV1ZUHAgOcaCc"
    )
    PUBLIC_KEY: str = "106c561c9e3de75150aa63a7f7cf28ab136ce6bae16a2b5cd2f0afec72af52b9"
    CLIENT_ID: str = "1237397616845914205"
    CLIENT_SECRET: str = "SHtdaACxV1D1ryMwweo_h7lmcCZoebTZ"
    REDIRECT_URI: str = "https://x.X.sh/login"
    CDN_API_KEY: str = "3nXGd7wMLvHreP"

class CLIENT:
    """
    Main client class.
    """
    PREFIX: str = ";"
    DESCRIPTION: str | None = None
    OWNER_IDS: list[int] = [
        585689685771288600,
        987183275560820806,
        # 1247076592556183598,
        320288667329495040,
        930383131863842816,
        442626774841556992
    ]
    SUPPORT_URL: str = "https://discord.gg/evict"
    INVITE_URL: str = (
        "https://discord.com/oauth2/authorize?client_id=1203514684326805524&permissions=8&scope=bot"
    )
    TWITCH_URL: str = (
        "https://twitch.tv/evictbot"
    )
    BACKEND_HOST: str = "api.evict.bot"
    FRONTEND_HOST: str = "evict.bot"
    WARP: str = "http://127.1:40000"

class LOGGER:
    """
    Change the bots logging channels.
    """
    MAIN_GUILD: int = 892675627373699072
    LOGGING_GUILD: int = 1318473085032071178
    TESTING_GUILD: int = ""
    COMMAND_LOGGER: int = 1319467001051090956
    STATUS_LOGGER: int = 1319470623071670295
    GUILD_JOIN_LOGGER: int = 1319466970474610708
    GUILD_BLACKLIST_LOGGER: int = 1319467116553830460
    USER_BLACKLIST_LOGGER: int = 1319467099969556542

class LAVALINK:
    """
    Lavalink authentication node.
    """
    NODE_COUNT: int = 1
    HOST: str = "127.0.0.1"
    PORT: int = 2333
    # PASSWORD: str = "Rb`$GX!pS@R*1t^0>&;n_C|Bg&0l+89}&CJ&B<v%H[^|9(Gd7A"
    PASSWORD: str = "youshallnotpass"

class NETWORK:
    """
    Main IPC authentication class.
    """
    HOST: str = "0.0.0.0"
    PORT: int = 6000
    
class DATABASE:
    """
    Postgres authentication class.
    """
    DSN: str = "postgres://postgres:admin@localhost/evict"

class REDIS:
    """
    Redis authentication class.
    """
    DB: int = 0
    HOST: str = "localhost"
    PORT: int = 6379

class AUTHORIZATION:
    """
    API keys for various services.
    """
    FNBR: str = "20490584-82aa-4ac3-8831-73d411d7c3d2"
    CLEVER: str = "CC9db9SL-aX3lL2t0GLBfTTkTug"
    WOLFRAM: str = "W95RJG-RRUXURP6XY"
    WEATHER: str = "0c5b47ed5774413c90b155456223004"
    OSU: str = "69c45249d9df06a933041e8da565392b458f80fc"
    LASTFM: list[str] = [
        "419e14665806ce4075565abe456a7bd4",
    ]
    SOUNDCLOUD: str = "OAuth 2-292593-994587358-Af8VbLnc6zIplJ"
    GEMINI: str = "AIzaSyCjgGH83OyUblhY4JHMQFJ5j3UVH5ztkaA"
    KRAKEN: str = "NjEyZTQyMzIwZTE4OWQ3OeLx-wiasK1ZCCKRbrPE13dJfF64AetJ4HvFef4w9c0s"
    FERNET_KEY: str = "0GKftpvX45aoHDZ1p4_OgYuaoPnI2TEPnJGeuvPjXjg="
    PIPED_API: str = "pipedapi.adminforge.de"
    JEYY_API: str = "74PJ0CPO6COJ6C9O6OPJGD1I70OJC.CLR6IORK.lkpD588_z_FMB40-Nl6L1w"
    OPENAI: str = (
     "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"
    )
    LOVENSE: str = "-X1p4MV3pUVZoygskhfrkisx69F7y2LJJzglk_d51s-rackNZPcogzu48d5Z4EHD"

    class GOOGLE:
        """
        Google API class.
        """
        CX: str = "b7498d486b2d19b97"
        KEY: str = "AIzaSyDHcNBPqv-GpTR6_oyA6EnTyiRXeGUjokI"

    class TWITCH:
        """
        Twitch API class.
        """
        CLIENT_ID: str = "30guvrlrw4lvf3knqsbin99asxdg4t"
        CLIENT_SECRET: str = "pxfuxxo2mn5qebq5xrl8g31ryh91gz"

    class SPOTIFY:
        """
        Spotify API class.
        """
        CLIENT_ID: str = "908846bb106d4190b4cdf5ceb3d1e0e5"
        CLIENT_SECRET: str = "d08df8638ee44bdcbfe6057a5e7ffd78"

    class REDDIT:
        """
        Reddit API class.
        """
        CLIENT_ID: str = "gM_QdMnswc2geCIvlbTkdQ"
        CLIENT_SECRET: str = "sMnPrsejKe5btrGPULuYrVOjMpAXkA"

    class BACKUPS:
        """
        BunnyCDN backups authentication class.
        """
        HOST: str = "ny.storage.bunnycdn.com"
        USER: str = "evict-backups"
        PASSWORD: str = "bb6dd9ef-1a8a-412f-83f3c9ac5ec1-468e-4f9c"

    class AVH:
        """
        BUNNYCDN AVH authentication class.
        """
        URL: str = "https://storage.bunnycdn.com/evict/avh/"
        ACCESS_KEY: str = "10e0eb5f-79de-4ae9-a35a9b9f71e0-8c99-4a58"

    class SOCIALS:
        """
        BUNNYCDN SOCIALS authentication class.
        """
        URL: str = "https://storage.bunnycdn.com/evict/socials/"
        ACCESS_KEY: str = "10e0eb5f-79de-4ae9-a35a9b9f71e0-8c99-4a58"

class EMOJIS:
    """
    Controls the emojis throughout the bot.
    """
    class FUN:
        LESBIAN: str = "<:lesbian:1300034112987598890>"
        GAY: str = "<:gay:1300034800257732719> "
        DUMBASS: str = "<:dumbass:1339465205914144819> "
    
    class ECONOMY:
        """
        Changes the emojis on the economy commands.
        """
        WELCOME: str = "<a:welcome:1332951722271703070>"
        COMMAND: str = "<:command:1333095008286408795>"
        GEM: str = "<a:gem:1332951453589049456>"
        CROWN: str = "<:crown:1320338275570946120>"
        INVIS: str = "<:invis:1333300029460582400>"
    
    class POLL:
        """
        Change the emojis used on the poll embeds.
        """
        BLR: str = "<:evict_blr:1263759792439169115>"
        SQUARE: str = "<:evict_sqaure:1263759807417028649>"
        BRR: str = "<:evict_brr:1263759798751461377>"
        WLR: str = "<:white_left_rounded:1263743905120387172>"
        WHITE: str = "<:white:1263743898145001517>"
        WRR: str = "<:white_right_rounded:1263743912221216862>"

    class STAFF:
        """
        Changes the emojis on staff commands.
        """
        DEVELOPER: str = "<:developer:1325012518006947861>"
        HEADSTAFF: str = "<:headstaff:1351038626854731776>"
        HEADQA: str = "<:headqa:1351038645502476359>"
        OWNER: str = "<:owner:1325012419587866666>"
        SUPPORT: str = "<:support:1325012723922370601>"
        TRIAL: str = "<:trial:1323255897656397824>"
        MODERATOR: str = "<:mod:1325081613238931457>"
        DONOR: str = "<:donor1:1320054420616249396>"
        INSTANCE: str = "<:donor4:1320428908406902936>"
        STAFF: str = "<:staff:1325012421819236443>"

    class INTERFACE:
        """
        Changes the emojis on the VoiceMaster Panel.
        """
        LOCK: str = "<:lock:1263727069095919698>"
        UNLOCK: str = "<:unlock:1263730907680870435>"
        GHOST: str = "<:hide:1263731781157392396>"
        REVEAL: str = "<:reveal:1263731670121709568>"
        CLAIM: str = "<:claim:1263731873167708232>"
        DISCONNECT: str = "<:hammer:1292838404597354637>"
        ACTIVITY: str = "<:activity:1292838226125656097>"
        INFORMATION: str = "<:information:1263727043967717428>"
        INCREASE: str = "<:increase:1263731093845315654>"
        DECREASE: str = "<:decrease:1263731510239035442>"

    class PAGINATOR:
        """
        Changes the emojis on the paginator.
        """
        NEXT: str = "<:right:1263727130370637995>"
        NAVIGATE: str = "<:filter:1263727034798968893>"
        PREVIOUS: str = "<:left:1263727060078035066>"
        CANCEL: str = "<:deny:1263727013433184347>"

    class AUDIO:
        """
        Changes the emojis on the audio panel.
        """
        SKIP: str = "<:skip:1243011308333564006>"
        RESUME: str = "<:resume:1243011309449252864>"
        REPEAT: str = "<:repeat:1243011309843382285>"
        PREVIOUS: str = "<:previous:1243011310942162990>"
        PAUSE: str = "<:pause:1243011311860842627>"
        QUEUE: str = "<:queue:1243011313006022698>"
        REPEAT_TRACK: str = "<:repeat_track:1243011313660334101>"

    class ANTINUKE:
        """
        Changes the emojis on the Antinuke-Config command.
        """
        ENABLE: str = "<:enable:1263758811429343232>"
        DISABLE: str = "<:disable:1263758691858120766>"

    class BADGES:
        """
        Changes the emojis that show on badges.
        """
        HYPESQUAD_BRILLIANCE: str = "<:hypesquad_brillance:1289500479117590548>"
        BOOST: str = "<:booster:1263727083310415885>"
        STAFF: str = "<:staff:1263729127199084645>"
        VERIFIED_BOT_DEVELOPER: str = "<:earlydev:1263727027022860330>"
        SERVER_OWNER: str = "<:owner:1329251274440310834>"
        HYPESQUAD_BRAVERY: str = "<:hypesquad_bravery:1289500873830961279>"
        PARTNER: str = "<:partner:1263727124066340978>"
        HYPESQUAD_BALANCE: str = "<:hypesquad_balance:1289500688052785222>"
        EARLY_SUPPORTER: str = "<:early:1263727021318602783>"
        HYPESQUAD: str = "<:hypesquad:1289501069449236572>"
        BUG_HUNTER_LEVEL_2: str = "<:buggold:1263726960882876456>"
        CERTIFIED_MODERATOR: str = "<:certified_moderator:1289501261640765462>"
        NITRO: str = "<:nitro:1289499927117828106>"
        BUG_HUNTER: str = "<:bugreg:1263726968377966642>"
        ACTIVE_DEVELOPER: str = "<:activedev:1263726943048695828>"

    class CONTEXT:
        """
        Changes the emojis on context.
        """
        APPROVE: str = "<:approve:1271155661451034666>"
        DENY: str = "<:deny:1263727013433184347>"
        WARN: str = "<:warn:1263727178802004021>"
        FILTER: str = "<:filter:1263727034798968893>"
        LEFT: str = "<:left:1263727060078035066>"
        RIGHT: str = "<:right:1263727130370637995>"
        JUUL: str = "<:juul:1300217541909545000>"
        NO_JUUL: str = "<:no_juul:1300217551699181588>"

    class SOCIAL:
        """
        Changes the emojis on social commands.
        """
        DISCORD: str = "<:discord:1290120978306695281>"
        GITHUB: str = "<:github:1289507143887884383>"
        WEBSITE: str = "<:link:1290119682103316520>"

    class TICKETS:
        """
        Changes the emojis on tickets.
        """
        TRASH: str = "<:trash:1263727144832602164>"

    class SPOTIFY:
        """
        Changes the emojis on the Spotify commands.
        """
        LEFT: str = "<:left_spot:1322093955449487433>"
        RIGHT: str = "<:right_spot:1322094031551070219>"
        BLACK: str = "<:black:1322093844967456769>"
        BLACK_RIGHT: str = "<:blackright:1322093837992333404>"
        WHITE: str = "<:white_spot:1322094107044089877>"
        ICON: str = "<:spotify_cmd:1322094318890254359>"
        LISTENING: str = "<:listening:1322093224688488458>"
        SHUFFLE: str = "<:shuffle:1322093133449789481>"
        REPEAT: str = "<:repeat:1322093145789562902>"
        DEVICE: str = "<:devices:1322093261636108321>"
        NEXT: str = "<:next:1322093204492783657>"
        PREVIOUS: str = "<:previous:1322093173371174987>"
        PAUSE: str = "<:pause:1322093187883466803>"
        VOLUME: str = "<:volume:1322093120053055568>"
        FAVORITE: str = "<:fav:1322094614596947999>"
        REMOVE: str = "<:remove:1322094634163241021>"
        EXPLCIT: str = "<:explicit:1322093240941412386>"
    
    class LOVENSE:
        """
        Changes the emojis on the Lovense commands.
        """
        LOVENSE: str = "<:lovense:1321525243549974539>"
        KEY: str = "b5c0e61d3ff07bf8"
        IV: str = "EAB712083AB0310A"
    
    class DOCKET: 
        """
        Change the emojis on the commands relating to Docket.
        """
        INFO: str = "<:info:1320338239139348554>"
        YELLOW: str = "<:yellow:1324416184539549817>"
        BLACK: str = "<:black:1324415916045238273> "
        PURPLE: str = "<:purple:1324415931929202688>"
        RED: str =  "<:red:1324416002062159972>"
        CYAN: str = "<:cyan:1324416598827860079>"
    
    class MISC:
        """
        Miscellaneous emojis used throughout the bot.
        """
        CONNECTION: str = "<:connection:1300775066933530755>"
        CRYPTO: str = "<:crypto:1323197786111606847>"
        BITCOIN: str = "<:bitcoin:1323197068734632031>"
        ETHEREUM: str = "<:ethereum:1323197076238237758>"
        XRP: str = "<:XRP:1323197083603177472>"
        LITECOIN: str = "<:LTC:1323197091933327360>"
        EXTRA_SUPPORT: str = "<:extra_support:1331659705709236264>"
        SECURITY: str = "<:security:1331659736386637834>"
        ANAYLTICS: str = "<:analytics:1331659734637609141>"
        REDUCED_COOLDOWNS: str = "<:reduced_cooldown:1331659608116297788>"
        AI: str = "<:ai:1331659592630800477>"
        MODERATION: str = "<:moderator:1325012416035033139>"
        COMMANDS: str = "<:donor4:1320428908406902936>"

class ROLES:
    """
    Changes the roles on the bot.
    """
    MODERATOR: int = 1325007612797784144
    TRIAL: int = 1323255508609663098
    DEVELOPER: int = 1265473601755414528
    HEADSTAFF: int = 1330750312553644176
    HEADQA: int = 1340989544656277565
    SUPPORT: int = 1264110559989862406
    DONOR: int = 1318054098666389534
    INSTANCE: int = 1320428924215496704

class COLORS:
    """
    Changes the colors on context outputs.
    """
    NEUTRAL: int = 0xCCCCFF
    APPROVE: int = 0xCCCCFF
    WARN: int = 0xCCCCFF
    DENY: int = 0xCCCCFF
    SPOTIFY: int = 0x1DB954

class ECONOMY:
    """
    Changes the chances on economy commands.
    """
    CHANCES = {
        "roll": {"percentage": 50.0, "total": 100.0},
        "coinflip": {"percentage": 50.0, "total": 100.0},
        "gamble": {"percentage": 20.0, "total": 100.0},
        "supergamble": {"percentage": 50.0, "total": 1000.0},
    }

class RATELIMITS:
    """
    Changes the rate limits on the bot.
    """
    PER_10S: int = 20
    PER_30S: int = 35
    PER_1M: int = 65