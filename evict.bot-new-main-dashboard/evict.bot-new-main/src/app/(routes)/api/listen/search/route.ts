export async function GET(request: Request) {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('query')
    
    const response = await fetch(
        `https://listen.squareweb.app/search?query=${query}&key=${process.env.LISTEN_API_KEY}&userId=930383131863842816`
    )
    const data = await response.json()
    return Response.json(data)
}