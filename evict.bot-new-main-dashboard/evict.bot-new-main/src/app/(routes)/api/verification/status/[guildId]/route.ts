import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"

export async function GET(
  request: NextRequest,
  { params }: { params: { guildId: string } }
) {
  const session = await auth()
  if (!session?.user?.userToken) {
    return new NextResponse("Unauthorized", { status: 401 })
  }

  try {
    const response = await fetch(`https://api.evict.bot/verification/status/${params.guildId}`, {
      headers: {
        Authorization: `Bearer ${session.user.userToken}`,
      },
    })

    if (!response.ok) {
      throw new Error("Failed to fetch verification status")
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    return new NextResponse("Internal Server Error", { status: 500 })
  }
}