import asyncio
import logging
import os
import tempfile

from typing import Literal, Dict, Set, Callable, Any
from pathlib import Path
from io import BytesIO
from xxhash import xxh64_hexdigest

from discord import File
from discord.ext.commands import Context, CommandError

from vesta.framework.tools.converters import PartialAttachment

logger = logging.getLogger(__name__)

VIDEO_OPERATIONS: Set[str] = {"april-fools", "ah-shit", "reverse"}

GIF_OPERATIONS: Set[str] = {
    "gif-magik",
    "ghost",
    "spin",
    "zoom",
    "rainbow",
    "toaster",
    "rubiks",
    "flag2",
    "flag",
    "speech-bubble",
    "heart-locket",
    "swirl",
    "wormhole",
    "caption",
    "spread",
    "book",
    "tattoo",
    "fisheye",
    "neon",
    "invert",
    "deepfry",
    "circuitboard",
    "meme",
}

PARAMETER_HANDLERS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "caption": lambda p: f"caption[text={p['text']}]" if "text" in p else "caption",
    "flag": lambda p: f"flag[flag={p['flag']}]" if "flag" in p else "flag",
    "flag2": lambda p: f"flag2[flag={p['flag']}]" if "flag" in p else "flag2",
    "ghost": lambda p: f"ghost[depth={p['depth']}]" if "depth" in p else "ghost",
    "blur": lambda p: f"blur[strength={p['radius']}]" if "radius" in p else "blur",
    "rotate": lambda p: f"rotate[angle={p['angle']}]" if "angle" in p else "rotate",
    "speed": lambda p: f"speed[factor={p['factor']}]" if "factor" in p else "speed",
    "resize": lambda p: (
        f"resize[width={p['width']},height={p['height']}]"
        if all(k in p for k in ["width", "height"])
        else "resize"
    ),
    "swirl": lambda p: (
        f"swirl[strength={p['strength']}]" if "strength" in p else "swirl"
    ),
    "heart-locket": lambda p: (
        f"heart-locket[text={p['text']}]" if "text" in p else "heart-locket"
    ),
    "motivate": lambda p: (
        f"motivate[{';'.join([f'{k}={p[k]}' for k in ['top', 'bottom'] if k in p and p[k]])}]"
        if any(k in p for k in ["top", "bottom"])
        else "motivate"
    ),
    "meme": lambda p: (
        f"meme[{';'.join([f'{k}={p[k]}' for k in ['top', 'bottom'] if k in p and p[k]])}]"
        if any(k in p for k in ["top", "bottom"])
        else "meme"
    ),
    "bloom": lambda p: (
        f"bloom[{';'.join([f'{k}={p[k]}' for k in ['radius', 'brightness', 'sharpness'] if k in p])}]"
        if any(k in p for k in ["radius", "brightness", "sharpness"])
        else "bloom"
    ),
}


async def get_output_extension(operation: str, input_format: str) -> str:
    """
    Determine the output file extension based on operation and input format.
    """
    if operation in VIDEO_OPERATIONS:
        return "mp4"
    if operation in GIF_OPERATIONS or input_format == "gif":
        return "gif"
    return "png"


async def write_buffer_to_file(buffer: BytesIO, path: str) -> None:
    """
    Write buffer data to a file.
    """
    try:
        data = buffer.getvalue() if hasattr(buffer, "getvalue") else buffer
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        raise CommandError(f"Failed to write file: {e}")


async def run_flux_command(cmd: list, flux_dir: str) -> None:
    """
    Run the flux command and handle errors.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=flux_dir,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise CommandError(f"Flux processing failed: {error_msg}")
    except asyncio.SubprocessError as e:
        raise CommandError(f"Flux subprocess error: {str(e)}")
    except Exception as e:
        raise CommandError(f"Flux processing failed: {str(e)}")


async def flux(
    ctx: Context,
    operation: Literal[
        "caption",
        "speech-bubble",
        "flag2",
        "april-fools",
        "back-tattoo",
        "billboard-cityscape",
        "book",
        "circuitboard",
        "flag",
        "fortune-cookie",
        "heart-locket",
        "rubiks",
        "toaster",
        "valentine",
        "ah-shit",
        "bloom",
        "blur",
        "deepfry",
        "fisheye",
        "flip-flop",
        "frame-shift",
        "frames",
        "ghost",
        "gif",
        "globe",
        "grayscale",
        "info",
        "invert",
        "jpeg",
        "magik",
        "gif-magik",
        "meme",
        "motivate",
        "neon",
        "overlay",
        "paint",
        "ping-pong",
        "pixelate",
        "posterize",
        "rainbow",
        "resize",
        "reverse",
        "rotate",
        "scramble",
        "set-loop",
        "speed",
        "spin",
        "spread",
        "swirl",
        "uncaption",
        "wormhole",
        "zoom",
        "zoom-blur",
    ],
    attachment: PartialAttachment,
    **payload,
) -> File:
    """
    Process an image or GIF using the flux command line tool.
    """
    if not attachment or not attachment.buffer:
        raise CommandError("No valid attachment provided")

    flux_dir = Path("vesta/framework/flux")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_ext = ".gif" if attachment.format == "gif" else ".png"
        output_ext = await get_output_extension(operation, attachment.format)

        input_path = os.path.join(temp_dir, f"input{input_ext}")
        output_path = os.path.join(temp_dir, f"output.{output_ext}")

        await write_buffer_to_file(attachment.buffer, input_path)

        operation_str = PARAMETER_HANDLERS.get(operation, lambda p: operation)(payload)
        cmd = ["flux", "-i", input_path, "-o", operation_str, output_path]

        await run_flux_command(cmd, str(flux_dir))

        try:
            with open(output_path, "rb") as f:
                buffer = BytesIO(f.read())

            name = xxh64_hexdigest(buffer.getvalue())
            return File(buffer, filename=f"{operation.upper()}{name}FLUX.{output_ext}")
        except FileNotFoundError:
            raise CommandError(f"Output file not found at {output_path}")
        except Exception as e:
            raise CommandError(f"Failed to process output file: {e}")
