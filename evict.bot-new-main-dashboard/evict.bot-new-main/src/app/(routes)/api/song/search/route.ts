export async function GET(req: Request) {
    const url = new URL(req.url);
    const query = url.searchParams.get('q');

    if (!query) {
        return Response.json({ error: 'Missing search query' }, { status: 400 });
    }

    try {
        const [tracksResponse, artistsResponse] = await Promise.all([
            fetch(`http://ws.audioscrobbler.com/2.0/?method=track.search&track=${encodeURIComponent(query)}&api_key=${process.env.LASTFM_API_KEY}&format=json&limit=5`),
            fetch(`http://ws.audioscrobbler.com/2.0/?method=artist.search&artist=${encodeURIComponent(query)}&api_key=${process.env.LASTFM_API_KEY}&format=json&limit=5`)
        ]);

        const [tracksData, artistsData] = await Promise.all([
            tracksResponse.json(),
            artistsResponse.json()
        ]);

        const tracks = await Promise.all(
            tracksData.results?.trackmatches?.track?.map(async (track: any) => {
                const deezerSearch = await fetch(`https://api.deezer.com/search/track?q=${encodeURIComponent(`${track.name} ${track.artist}`)}&limit=1`);
                const deezerData = await deezerSearch.json();
                const deezerTrack = deezerData.data?.[0];

                return {
                    name: track.name,
                    artist: track.artist,
                    url: track.url,
                    listeners: parseInt(track.listeners),
                    image: deezerTrack?.album?.cover_medium || null
                };
            }) || []
        );

        const artists = await Promise.all(
            artistsData.results?.artistmatches?.artist?.map(async (artist: any) => {
                const deezerSearch = await fetch(`https://api.deezer.com/search/artist?q=${encodeURIComponent(artist.name)}&limit=1`);
                const deezerData = await deezerSearch.json();
                const deezerArtist = deezerData.data?.[0];

                return {
                    name: artist.name,
                    url: artist.url,
                    listeners: parseInt(artist.listeners),
                    image: deezerArtist?.picture_medium || null
                };
            }) || []
        );

        return Response.json({ tracks, artists });
    } catch (error) {
        console.error('Error searching music:', error);
        return Response.json({ error: 'Failed to search music' }, { status: 500 });
    }
}