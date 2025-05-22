from api.shared import Media, BaseModel, Field, computed_field
from datetime import datetime
from typing import List, Optional
from .user import SimpleUser, InstagramUser

class PostStatistics(BaseModel):
    likes: int = Field(default=0)
    comments: int = Field(default=0)

class Post(BaseModel):
    id: str
    shortcode: str
    caption: Optional[str] = Field(default=None)
    taken_at: datetime = Field(validation_alias="taken_at_timestamp")
    media: List[Media] = Field(description="Redistributed media files.", default=[])
    user: SimpleUser | InstagramUser
    statistics: PostStatistics = Field()

    @computed_field
    @property
    def url(self) -> str:
        return f"https://www.instagram.com/p/{self.shortcode}"