export async function GET(request: Request) {
    const { searchParams } = new URL(request.url)
    const title = searchParams.get('title')
    const author = searchParams.get('author')
    
    const response = await fetch(
        `https://listen.squareweb.app/autoplay?title=${title}&author=${author}&algorithm=DYNAMIC&key=${process.env.LISTEN_API_KEY}`
    )
    const data = await response.json()
    return Response.json(data)
}