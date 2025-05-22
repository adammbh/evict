import aiohttp
import discord
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TypedDict, cast
from discord.ext.commands import command, Cog
from cashews import cache

from vesta.framework import Vesta, Context


class Location(TypedDict):
    lat: float
    lng: float


class Geometry(TypedDict):
    location: Location


class Photo(TypedDict):
    photo_reference: str
    width: int
    height: int


class PlaceDetails(TypedDict):
    name: str
    formatted_address: str
    rating: float
    user_ratings_total: int
    photos: List[Photo]
    geometry: Geometry
    website: str
    formatted_phone_number: str
    price_level: int
    place_id: str


class PlaceResult(TypedDict):
    result: PlaceDetails
    status: str
    error_message: Optional[str]


class PlaceSearchResult(TypedDict):
    results: List[PlaceDetails]
    status: str
    error_message: Optional[str]


@dataclass
class GoogleMapsAPI:
    """
    Wrapper for Google Maps API interactions.
    """

    api_key: str
    base_url: str = "https://maps.googleapis.com/maps/api"

    @cache(ttl=3600)  # 1 hour cache
    async def search_places(self, query: str, location: Optional[str] = None) -> Dict:
        """Search for places using text query"""
        async with aiohttp.ClientSession() as session:
            params = {
                "query": query,
                "key": self.api_key,
            }

            if location:
                params["location"] = location
                params["radius"] = "50000"

            url = f"{self.base_url}/place/textsearch/json"
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()

                return {
                    "status": "ERROR",
                    "error_message": f"API request failed with status {resp.status}",
                    "results": [],
                }

    @cache(ttl=86400)
    async def get_place_details(self, place_id: str) -> Dict:
        """
        Get detailed information about a specific place.
        """
        fields = (
            "name,formatted_address,rating,user_ratings_total,photos,"
            "geometry,opening_hours,website,formatted_phone_number,price_level,reviews"
        )

        async with aiohttp.ClientSession() as session:
            params = {"place_id": place_id, "fields": fields, "key": self.api_key}

            url = f"{self.base_url}/place/details/json"
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()

                return {
                    "status": "ERROR",
                    "error_message": f"API request failed with status {resp.status}",
                    "result": {},
                }

    @cache(ttl=1800)
    async def get_nearby_places(
        self,
        location: str,
        keyword: Optional[str] = None,
        place_type: Optional[str] = None,
        radius: int = 5000,
    ) -> Dict:
        """
        Find places near a specific location.
        """
        async with aiohttp.ClientSession() as session:
            params = {"location": location, "radius": radius, "key": self.api_key}

            if keyword:
                params["keyword"] = keyword

            if place_type:
                params["type"] = place_type

            url = f"{self.base_url}/place/nearbysearch/json"
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()

                return {
                    "status": "ERROR",
                    "error_message": f"API request failed with status {resp.status}",
                    "results": [],
                }

    def get_photo_url(self, photo_reference: str, max_width: int = 400) -> str:
        """Generate URL for a place photo"""
        return (
            f"{self.base_url}/place/photo?"
            f"maxwidth={max_width}&"
            f"photo_reference={photo_reference}&"
            f"key={self.api_key}"
        )


class GoogleMapsService:
    """Google Maps service for Discord bot integration"""

    def __init__(self, bot: Vesta):
        self.bot = bot
        self.api_key = os.getenv("GOOGLE_KEY", "")
        self.maps = GoogleMapsAPI(self.api_key)

    @cache(ttl=3600)
    async def create_place_embed(self, place_data: Dict) -> discord.Embed:
        """Create a Discord embed for a place"""
        result = place_data.get("result", {})

        if not result:
            return discord.Embed(
                title="Place not found",
                description="No information available for this place.",
            )

        name = result.get("name", "Unknown Place")
        address = result.get("formatted_address", "No address available")
        rating = result.get("rating", 0)
        total_ratings = result.get("user_ratings_total", 0)

        embed = discord.Embed(title=name, description=address)

        # Add rating with stars
        if rating:
            full_stars = int(rating)
            stars = "★" * full_stars + "☆" * (5 - full_stars)
            embed.add_field(
                name="Rating",
                value=f"{stars} {rating} ({total_ratings:,})",
                inline=False,
            )

        # Add photo if available
        photos = result.get("photos", [])
        if photos and (photo_ref := photos[0].get("photo_reference")):
            embed.set_image(url=self.maps.get_photo_url(photo_ref, 800))

        # Add website if available
        if website := result.get("website"):
            embed.add_field(name="Website", value=website, inline=False)

        # Add phone number if available
        if phone := result.get("formatted_phone_number"):
            embed.add_field(name="Phone", value=phone, inline=True)

        # Add price level if available
        if (price_level := result.get("price_level")) is not None:
            price_str = "💰" * price_level if price_level > 0 else "Free"
            embed.add_field(name="Price Level", value=price_str, inline=True)

        # Add footer with coordinates for map link
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})
        lat, lng = location.get("lat"), location.get("lng")

        if lat and lng:
            place_id = place_data.get("place_id", result.get("place_id"))
            map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            if place_id:
                map_url += f"&query_place_id={place_id}"
            embed.url = map_url
            embed.set_footer(text=f"Lat: {lat}, Lng: {lng}")

        return embed

    async def search_command(self, ctx: Context, query: str) -> None:
        """Handle maps search command"""
        async with ctx.typing():
            search_results = await self.maps.search_places(query)

            if search_results.get("status") != "OK":
                await ctx.embed(
                    f"Error: {search_results.get('error_message', 'Unknown error')}",
                    "warned",
                )
                return

            results = search_results.get("results", [])

            if not results:
                await ctx.embed(f"No places found for '{query}'", "warned")
                return

            # Get details for the first result
            place_id = results[0].get("place_id")
            place_details = await self.maps.get_place_details(place_id)

            embed = await self.create_place_embed(place_details)

            # TODO: Add pagination for multiple results
            await ctx.send(embed=embed)

    async def nearby_command(
        self, ctx: Context, query: str, location: Optional[str] = None
    ) -> None:
        """Handle nearby places command"""
        async with ctx.typing():
            # Default to Washington DC if no location provided
            location = location or "38.8977,-77.0365"

            nearby_results = await self.maps.get_nearby_places(location, keyword=query)

            if nearby_results.get("status") != "OK":
                await ctx.embed(
                    f"Error finding nearby places: {nearby_results.get('error_message', 'Unknown error')}",
                    "warned",
                )
                return

            results = nearby_results.get("results", [])

            if not results:
                await ctx.embed(f"No nearby '{query}' found", "warned")
                return

            # Create map embed with multiple locations
            embed = discord.Embed(title=f"Nearby {query} Locations")

            # Add static map with markers
            marker_params = [
                f"markers=color:red%7C{r['geometry']['location']['lat']},{r['geometry']['location']['lng']}"
                for r in results[:10]
            ]

            map_url = (
                f"https://maps.googleapis.com/maps/api/staticmap?"
                f"center={location}&zoom=12&size=600x300&maptype=roadmap&"
                f"{markers}&key={self.api_key}"
            )
            embed.set_image(url=map_url)

            # List the first 5 places
            descriptions = []
            for i, place in enumerate(results[:5], 1):
                name = place.get("name", "Unknown")
                vicinity = place.get("vicinity", "No address")
                rating = place.get("rating", 0)

                stars = ""
                if rating:
                    stars = "★" * int(rating) + "☆" * (5 - int(rating))

                descriptions.append(
                    f"**{i}. {name}**\n{vicinity}\n{stars} {rating if rating else 'No rating'}\n"
                )

            embed.description = "\n".join(descriptions)
            await ctx.send(embed=embed)


class GoogleMaps(Cog):
    """Google Maps commands for Discord"""

    def __init__(self, bot: Vesta):
        self.bot = bot
        self.maps_service = GoogleMapsService(bot)

    @command()
    async def maps(self, ctx: Context, *, query: str) -> None:
        """Search for a place on Google Maps"""
        await self.maps_service.search_command(ctx, query)

    @command()
    async def nearby(
        self, ctx: Context, query: str, *, location: Optional[str] = None
    ) -> None:
        """Find nearby places on Google Maps"""
        await self.maps_service.nearby_command(ctx, query, location)
