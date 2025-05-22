from typing import List, Optional
from pydantic import BaseModel


class Definition(BaseModel):
    text: str
    examples: List[str] = []
    part_of_speech: Optional[str] = None
    etymology: Optional[str] = None
    synonyms: List[str] = []


class WordEntry(BaseModel):
    word: str
    definitions: List[Definition]
    pronunciation: Optional[str] = None
