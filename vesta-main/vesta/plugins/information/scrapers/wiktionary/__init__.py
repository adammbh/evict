from __future__ import annotations

from typing import List, Optional
import aiohttp
from cashews import cache
from logging import getLogger

from .models import WordEntry, Definition

logger = getLogger("wiktionary")

API_ENDPOINT = "https://en.wiktionary.org/w/api.php"


@cache(ttl="1d")
async def get_word_definition(word: str) -> Optional[WordEntry]:
    """Fetch word definition using Wiktionary's API"""

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": word,
        "explaintext": "1",
        "exsectionformat": "plain",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_ENDPOINT, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                pages = data["query"]["pages"]
                page = next(iter(pages.values()))

                if "missing" in page or "extract" not in page:
                    return None

                content = page["extract"]

                definitions: List[Definition] = []
                pronunciation = None
                in_noun_section = False
                current_synonyms = []

                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    if not pronunciation and line.count("/") >= 2:
                        try:
                            start = line.find("/")
                            end = line.find("/", start + 1)
                            if start != -1 and end != -1:
                                pronunciation = line[start : end + 1]
                        except:
                            pass

                    if any(x in line for x in [":", "Episode", "Season", "Graham"]):
                        continue

                    if line.lower() == "noun" or line.lower().startswith("noun "):
                        in_noun_section = True
                        continue

                    if in_noun_section and line.lower().startswith("synonyms:"):
                        syn_text = line[9:].strip()
                        current_synonyms = [
                            s.strip() for s in syn_text.split(",") if s.strip()
                        ]
                        continue

                    if not in_noun_section:
                        continue

                    if any(
                        line.lower().startswith(x)
                        for x in [
                            "verb",
                            "adjective",
                            "adverb",
                            "pronoun",
                            "preposition",
                            "synonyms",
                            "antonyms",
                            "hyponyms",
                            "derived",
                            "related",
                            "translations",
                            "references",
                            "see also",
                        ]
                    ):
                        continue

                    if (
                        line.startswith("(")
                        or (line[0].isdigit() and ". " in line)
                        or line.startswith("An ")
                        or line.startswith("A ")
                        or line.startswith("The ")
                    ):
                        if line[0].isdigit() and ". " in line:
                            line = line[line.find(". ") + 2 :]

                        def_text = clean_definition(line)
                        if def_text:
                            definitions.append(
                                Definition(
                                    text=def_text,
                                    part_of_speech="noun",
                                    synonyms=current_synonyms.copy(),
                                )
                            )
                            current_synonyms = []

                if not definitions:
                    return None

                return WordEntry(
                    word=word, definitions=definitions, pronunciation=pronunciation
                )

    except Exception as e:
        logger.exception(f"Error while fetching definition for '{word}': {str(e)}")
        return None


def clean_definition(text: str) -> str:
    """Clean up definition text by removing unwanted parts and formatting properly"""

    if not text:
        return ""

    if ": " in text:
        text = text.split(": ")[0]
    if "." in text:
        text = text.split(". ")[0] + "."

    if text.startswith("("):
        end_paren = text.find(")")
        if end_paren != -1:
            marker = text[1:end_paren].strip()
            rest = text[end_paren + 1 :].strip()
            if marker and rest:
                text = f"({marker}) {rest}"

    unwanted = ["[quotations", "[from", "(compare", "(contrast", "citation needed"]
    for marker in unwanted:
        if marker in text.lower():
            text = text[: text.lower().find(marker)].strip()

    if text:
        text = text[0].upper() + text[1:]
        if not text.endswith("."):
            text += "."

    return text
