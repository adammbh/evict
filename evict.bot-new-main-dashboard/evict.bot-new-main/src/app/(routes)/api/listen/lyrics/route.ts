export async function GET(request: Request) {
    const { searchParams } = new URL(request.url)
    const title = searchParams.get('title')
    const artist = searchParams.get('artist')
    
    const response = await fetch(
        `https://listen.squareweb.app/lyrics?title=${title}&artist=${artist}&key=${process.env.LISTEN_API_KEY}`
    )
    const data = await response.json()
    return Response.json(data)
}