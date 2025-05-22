import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"

export async function POST(
  request: NextRequest,
  { params }: { params: { guildId: string; userId: string } }
) {
  const session = await auth()
  if (!session?.user?.userToken) {
    return NextResponse.json({ error: "MISSING_AUTHORIZATION" }, { status: 401 })
  }

  try {
    const body = await request.json()
    console.log('Verify request body:', body)
    
    if (body.answers) {
      const verifyResponse = await fetch(
        `https://api.evict.bot/verification/verify/${params.guildId}/${params.userId}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.user.userToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            session: body.session,
            answers: body.answers
          })
        }
      )

      if (!verifyResponse.ok) {
        const errorData = await verifyResponse.json()
        return NextResponse.json({ 
          success: false,
          message: errorData.message,
          error: errorData.error,
          code: errorData.code 
        }, { status: verifyResponse.status })
      }

      const data = await verifyResponse.json()
      return NextResponse.json(data)
    }

    if (body.token) {
      const payload = {
        secret: process.env.HCAPTCHA_SECRET_KEY!,
        response: body.token
      }
      console.log('hCaptcha verification payload:', payload)

      const hcaptchaResponse = await fetch('https://api.hcaptcha.com/siteverify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(payload)
      })

      const hcaptchaData = await hcaptchaResponse.json()
      console.log('hCaptcha response:', hcaptchaData)
      
      const apiPayload = {
        session: body.session,
        token: body.token,
        success: hcaptchaData.success,
        challenge_ts: hcaptchaData.challenge_ts
      }
      console.log('API verification payload:', apiPayload)
      
      const verifyResponse = await fetch(
        `https://api.evict.bot/verification/verify/${params.guildId}/${params.userId}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.user.userToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(apiPayload)
        }
      )

      if (!verifyResponse.ok) {
        const errorData = await verifyResponse.json()
        return NextResponse.json({ error: errorData.error || "INTERNAL_ERROR" }, { status: verifyResponse.status })
      }

      const data = await verifyResponse.json()
      return NextResponse.json(data)
    }
    
    const codeResponse = await fetch(
      `https://api.evict.bot/verification/email/code?session=${encodeURIComponent(body.session)}`,
      {
        headers: {
          Authorization: `Bearer ${session.user.userToken}`
        }
      }
    )

    const codeData = await codeResponse.json()
    console.log('Code response:', codeData)

    if (!codeData.valid) {
      return NextResponse.json({ error: "Invalid or expired verification code" }, { status: 400 })
    }

    const verifyResponse = await fetch(
      `https://api.evict.bot/verification/verify/${params.guildId}/${params.userId}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.user.userToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session: body.session,
          code: body.verification_data.email.code
        })
      }
    )

    if (!verifyResponse.ok) {
      const errorText = await verifyResponse.text()
      console.error('Verification failed:', errorText)
      return NextResponse.json({ error: "Verification failed" }, { status: verifyResponse.status })
    }

    const data = await verifyResponse.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Verification error:', error)
    return NextResponse.json({ error: "Verification failed" }, { status: 500 })
  }
}