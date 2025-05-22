from typing import Optional
from discord import (
    Message,
)
from discord.ext.commands import (
    BucketType,
    Cog,
    CommandError,
    cooldown,
    group,
    has_permissions,
)
from logging import getLogger

from vesta.framework import Vesta, Context
from vesta.framework.tools.converters import PartialAttachment


from .tools.flyx import flux

logger = getLogger(__name__)


class Media(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(
        name="media",
        invoke_without_command=True,
    )
    async def media(self, ctx: Context) -> None:
        """
        Image manipulation for photos, videos and GIFs
        """
        await ctx.send_help(ctx.command)

    @media.command(name="zoom")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def zoom(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Create a zooming gif using your photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="zoom-blur")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def zoom_blur(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Apply a zoom blur effect onto your photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom-blur", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="valentine")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def valentine(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Use your photo in a valentines gif.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "valentine", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="gifmagik")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def magik(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Create a gif of the magik filter being applied on a given photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "gif-magik", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="spin")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def spin(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Create a gif of your selected photo rotating clockwise.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "spin", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="rainbow")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def rainbow(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Apply an animated rainbow color effect to your photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "rainbow", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="toaster")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def toaster(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Generate your image on a toaster GIF.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "toaster", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="blur", example="5")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def blur(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        strength: Optional[int] = 5,
    ) -> Message:
        """
        Blur an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "blur", attachment, radius=strength)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="rubiks")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def rubiks(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put your image onto a rubiks cube.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "rubiks", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(
        name="motivate",
        example="url_goes_here hi low",
    )
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def motivate(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Create a motivation meme using your image and custom text.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        top_text = None
        bottom_text = None

        if text:
            parts = text.split(" ", 1)
            top_text = parts[0]
            if len(parts) > 1:
                bottom_text = parts[1]

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "motivate", attachment, top=top_text, bottom=bottom_text
                )
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="bloom")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def bloom(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Apply a bloom effect to your image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        radius = 10
        brightness = 15
        sharpness = 20

        if text:
            params = text.split()
            if len(params) >= 1:
                radius = int(params[0])
            if len(params) >= 2:
                brightness = int(params[1])
            if len(params) >= 3:
                sharpness = int(params[2])

        if not 0 <= radius <= 100:
            raise CommandError(
                f"**Value** must be between `0` and `100` but received `{radius}`"
            )
        if not 0 <= brightness <= 100:
            raise CommandError(
                f"**Value** must be between `0` and `100` but received `{brightness}`"
            )
        if not 0 <= sharpness <= 100:
            raise CommandError(
                f"**Value** must be between `0` and `100` but received `{sharpness}`"
            )

        async with ctx.typing():
            try:
                file = await flux(
                    ctx,
                    "bloom",
                    attachment,
                    radius=radius,
                    brightness=brightness,
                    sharpness=sharpness,
                )
                return await ctx.send(file=file)
            except ValueError:
                raise CommandError("Parameters must be numbers")
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="fortune")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def fortune(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put a given image inside a fortune cookie.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "fortune", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="flag")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def flag(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put a selected image onto a flag GIF.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "flag", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="magik")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def magik(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Apply the Magik filter to a photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "magik", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="meme")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def meme(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Create a meme with text.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        if not text:
            raise CommandError("You must provide text for the meme")

        parts = text.split(",", 1)
        top_text = parts[0].strip() if parts else None
        bottom_text = parts[1].strip() if len(parts) > 1 else None

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "meme", attachment, top=top_text, bottom=bottom_text
                )
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="flag2")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def flag2(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put a selected image onto a flag GIF.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "flag2", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="speechbubble")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def speechbubble(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Create a quotation meme using a photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "speech-bubble", attachment)
                return await ctx.send(file=file)

            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="heart")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def heart(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Create a heart gif with your desired photo and caption
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        if not text:
            await ctx.send_help(ctx.command)

        async with ctx.typing():
            try:
                file = await flux(ctx, "heart-locket", attachment, text=text)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="swirl")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def swirl(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Apply an animated swirl filter to a photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        strength = 2.0

        if text:
            try:
                strength = float(text)
            except ValueError:
                raise CommandError("**Value** must be a number")

        if not 0.0 <= strength <= 10.0:
            raise CommandError(
                f"**Value** must be between `0` and `10` but received `{strength}`"
            )

        async with ctx.typing():
            try:
                file = await flux(ctx, "swirl", attachment, strength=strength)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="caption")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def caption(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None, *, text: str
    ) -> Message:
        """
        Create your own caption meme using an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        if not text:
            await ctx.send_help(ctx.command)

        async with ctx.typing():
            try:
                file = await flux(ctx, "caption", attachment, text=text)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="circuitboard")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def circuitboard(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put your picture on a circuitboard GIF.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "circuitboard", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="spread")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def spread(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Apply a paint spread filter to a photo
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        strength = 5

        if text:
            try:
                strength = int(text)
            except ValueError:
                raise CommandError("**Value** must be a number")

        if not 0 <= strength <= 50:
            raise CommandError(
                f"**Value** must be between `0` and `50` but received `{strength}`"
            )

        async with ctx.typing():
            try:
                file = await flux(ctx, "spread", attachment, strength=strength)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="book")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def book(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put your image on a book.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "book", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="wormhole")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def wormhole(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Create a wormhole animation using a photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "wormhole", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="billboard")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def billboard(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Put your image on a billboard.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "billboard", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="pixelate")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def pixelate(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Pixelate an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        strength = 5.0

        if text:
            try:
                strength = float(text)
            except ValueError:
                raise CommandError("**Value** must be a number")

        if not 0.0 <= strength <= 50.0:
            raise CommandError(
                f"**Value** must be between `0` and `50` but received `{strength}`"
            )

        async with ctx.typing():
            try:
                file = await flux(ctx, "pixelate", attachment, strength=strength)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="tattoo")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def tattoo(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Tattoo your photo onto a body.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "tattoo", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="fisheye")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def fisheye(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Apply a fisheye lens effect to an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "fisheye", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="neon")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def neon(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Create a neon effect using the outlines in the picture provided.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        strength = 1.0

        if text:
            try:
                strength = float(text)
            except ValueError:
                raise CommandError("**Value** must be a number")

        if not 0.1 <= strength <= 5.0:
            raise CommandError(
                f"**Value** must be between `0.1` and `5.0` but received `{strength}`"
            )

        async with ctx.typing():
            try:
                file = await flux(ctx, "neon", attachment, strength=strength)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="grayscale")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def grayscale(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Convert an image to grayscale.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "grayscale", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="reverse")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def reverse(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Reverse an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "reverse", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="deepfry")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def deepfry(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Apply a deepfried filter to a photo.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "deepfry", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="invert")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def invert(
        self, ctx: Context, attachment: Optional[PartialAttachment] = None
    ) -> Message:
        """
        Invert an image.
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        async with ctx.typing():
            try:
                file = await flux(ctx, "invert", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="speed")
    @cooldown(1, 3, BucketType.user)
    @has_permissions(attach_files=True)
    async def speed(
        self,
        ctx: Context,
        attachment: Optional[PartialAttachment] = None,
        *,
        text: Optional[str] = None,
    ) -> Message:
        """
        Change the speed of a video
        """
        if attachment is None:
            attachment = await PartialAttachment.image_only_fallback(ctx)

        multiplier = 1.5

        if text:
            try:
                multiplier = float(text)
            except ValueError:
                raise CommandError("**Value** must be a number")

        if not 0.1 <= multiplier <= 15.0:
            raise CommandError(
                f"**Value** must be between `0.1` and `15.0` but received `{multiplier}`"
            )

        async with ctx.typing():
            try:
                file = await flux(ctx, "speed", attachment, multiplier=multiplier)
                return await ctx.send(file=file)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")
