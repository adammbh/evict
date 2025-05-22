from pydantic import BaseModel
from aiohttp import ClientSession
from lxml import html
from typing import Optional


class Snapchat(BaseModel):
    username: str
    display_name: str
    bitmoji_url: Optional[str] = None

    @classmethod
    async def from_username(cls, username: str):
        async with ClientSession() as session:
            async with session.get(
                f"https://www.snapchat.com/add/{username}"
            ) as response:
                if response.status != 200:
                    raise TypeError("User not found")

                tree = html.fromstring(await response.text())

                # Try multiple possible XPath patterns to find the image
                xpath_patterns = [
                    '//source[@type="image/webp"]/@srcset',
                    '//img[contains(@class, "bitmoji")]/@src',
                    '//img[contains(@alt, "Bitmoji")]/@src',
                    '//source[contains(@srcset, "bitmoji")]/@srcset',
                ]

                bitmoji_url = None
                for pattern in xpath_patterns:
                    results = tree.xpath(pattern)
                    if results:
                        bitmoji_url = results[0]
                        break

                # Get display name if available, fallback to username
                display_name = username
                name_patterns = [
                    '//h1[contains(@class, "name")]//text()',
                    '//span[contains(@class, "display-name")]//text()',
                ]

                for pattern in name_patterns:
                    results = tree.xpath(pattern)
                    if results:
                        display_name = results[0].strip()
                        break

                return cls(
                    username=username,
                    display_name=display_name,
                    bitmoji_url=bitmoji_url,
                )
