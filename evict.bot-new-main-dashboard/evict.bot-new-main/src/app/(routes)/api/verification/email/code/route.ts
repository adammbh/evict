import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"

const verificationCodes = new Map<string, string>()

export async function GET(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.userToken) {
    return new NextResponse("Unauthorized", { status: 401 })
  }

  const sessionParam = request.nextUrl.searchParams.get('session')
  if (!sessionParam) {
    return NextResponse.json({ error: "Missing session" }, { status: 400 })
  }

  const code = verificationCodes.get(sessionParam)
  if (!code) {
    return NextResponse.json({ error: "Code not found" }, { status: 404 })
  }

  return NextResponse.json({ code })
}

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.userToken) {
    return new NextResponse("Unauthorized", { status: 401 })
  }

  try {
    const body = await request.json()
    const { session: sessionParam, code, timestamp } = body

    if (!sessionParam || !code || !timestamp) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    if (Date.now() - timestamp > 30000) {
      return NextResponse.json({ error: "Request expired" }, { status: 400 })
    }

    verificationCodes.set(sessionParam, code)

    return NextResponse.json({ success: true })
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 })
  }
} 