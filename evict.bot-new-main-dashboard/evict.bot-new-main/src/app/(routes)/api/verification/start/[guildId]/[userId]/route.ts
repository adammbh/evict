import { auth } from "@/auth"
import sgMail, { MailDataRequired } from "@sendgrid/mail"
import crypto from "crypto"
import { NextRequest, NextResponse } from "next/server"

sgMail.setApiKey(process.env.SENDGRID_API_KEY!)

// Track email attempts with a Map of email -> { count, lastAttempt }
const emailAttempts = new Map<string, { count: number; lastAttempt: number }>()
const MAX_ATTEMPTS = 5
const RESET_PERIOD = 24 * 60 * 60 * 1000 // 24 hours in milliseconds

export async function POST(
    request: NextRequest,
    { params }: { params: { guildId: string; userId: string } }
) {
    const session = await auth()
    if (!session?.user?.userToken || !session?.user?.id) {
        return NextResponse.json({ error: "MISSING_AUTHORIZATION" }, { status: 401 })
    }

    try {
        const guildResponse = await fetch(
            `https://api.evict.bot/verification/status/${params.guildId}`,
            {
                headers: {
                    Authorization: `Bearer ${session.user.userToken}`
                }
            }
        )

        if (!guildResponse.ok) {
            const errorData = await guildResponse.json()
            return NextResponse.json(
                { error: errorData.error || "INTERNAL_ERROR" },
                { status: guildResponse.status }
            )
        }

        const guildData = await guildResponse.json()

        if (guildData.verified) {
            return NextResponse.json({ error: "ALREADY_VERIFIED" }, { status: 400 })
        }

        if (guildData.verification.method.type === "questions") {
            const startResponse = await fetch(
                `https://api.evict.bot/verification/start/${params.guildId}/${params.userId}`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${session.user.userToken}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        type: "questions"
                    })
                }
            )

            if (!startResponse.ok) {
                const errorData = await startResponse.json()
                if (errorData.error === "User is already verified") {
                    return NextResponse.json({ error: "ALREADY_VERIFIED" }, { status: 400 })
                }
                return NextResponse.json(
                    { error: errorData.error || "INTERNAL_ERROR" },
                    { status: startResponse.status }
                )
            }

            const data = await startResponse.json()
            return NextResponse.json(data)
        }

        const verificationCode =
            guildData.verification.method.type === "email"
                ? crypto.randomBytes(6).toString("hex").toUpperCase()
                : undefined

        const response = await fetch(
            `https://api.evict.bot/verification/start/${params.guildId}/${params.userId}`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${session.user.userToken}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    type: guildData.verification.method.type
                })
            }
        )

        if (!response.ok) {
            const errorData = await response.json()
            if (errorData.error === "User is already verified") {
                return NextResponse.json({ error: "ALREADY_VERIFIED" }, { status: 400 })
            }
            return NextResponse.json(
                { error: errorData.error || "INTERNAL_ERROR" },
                { status: response.status }
            )
        }

        const data = await response.json()

        if (guildData.verification.method.type === "email") {
            const userEmail = session.user.email!
            const attempts = emailAttempts.get(userEmail) || { count: 0, lastAttempt: 0 }

            if (Date.now() - attempts.lastAttempt > RESET_PERIOD) {
                attempts.count = 0
            }

            if (attempts.count >= MAX_ATTEMPTS) {
                return NextResponse.json({ error: "TOO_MANY_ATTEMPTS" }, { status: 429 })
            }

            try {
                await fetch("https://api.evict.bot/verification/email/code", {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${session.user.userToken}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session: data.session,
                        code: verificationCode,
                        timestamp: Date.now()
                    })
                })

                const msg: MailDataRequired = {
                    to: userEmail,
                    from: {
                        email: "noreply@evict.bot",
                        name: "Evict Verification"
                    },
                    templateId: process.env.SENDGRID_TEMPLATE_ID!,
                    subject: `Verify your access to ${guildData.guild_name}`,
                    dynamicTemplateData: {
                        subject: `Verify your access to ${guildData.guild_name}`,
                        verification_code: verificationCode,
                        guild_name: guildData.guild_name,
                        user_name: session.user.name,
                        expires_at: new Date(data.expires_at).toLocaleString()
                    }
                }

                await sgMail.send(msg)

                emailAttempts.set(userEmail, {
                    count: attempts.count + 1,
                    lastAttempt: Date.now()
                })
            } catch (error) {
                return NextResponse.json({ error: "INTERNAL_ERROR" }, { status: 500 })
            }
        }

        return NextResponse.json({
            session: data.session,
            expires_at: data.expires_at
        })
    } catch (error) {
        return NextResponse.json({ error: "INTERNAL_ERROR" }, { status: 500 })
    }
}
