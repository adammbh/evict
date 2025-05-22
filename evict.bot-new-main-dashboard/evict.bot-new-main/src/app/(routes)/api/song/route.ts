import { getSpotifyTrackId } from "@/libs/dashboard/music/spotify"

export async function GET(req: Request) {
    const url = new URL(req.url);
    const title = url.searchParams.get('title');
    const artist = url.searchParams.get('artist');

    if (!title || !artist) {
        return Response.json({ error: 'Missing title or artist' }, { status: 400 });
    }

    try {
        const [spotifyId, artistInfo] = await Promise.all([
            getSpotifyTrackId(artist, title),
            fetch(`http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=${encodeURIComponent(artist)}&api_key=${process.env.LASTFM_API_KEY}&format=json`)
                .then(res => res.json())
        ]);

        const lastfmData = artistInfo.artist;

        return Response.json({
            spotify: {
                trackId: spotifyId
            },
            artist: {
                name: lastfmData.name,
                url: lastfmData.url,
                bio: lastfmData.bio?.summary,
                listeners: parseInt(lastfmData.stats?.listeners),
                playcount: parseInt(lastfmData.stats?.playcount),
                tags: lastfmData.tags?.tag,
                similar: lastfmData.similar?.artist
            }
        });
    } catch (error) {
        console.error('Error fetching music info:', error);
        return Response.json({ error: 'Failed to fetch music info' }, { status: 500 });
    }
}