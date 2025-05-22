import { auth } from "@/auth"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
    try {
        const session = await auth()
        
        if (!session?.user) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
        }

        let body;
        try {
            body = await request.json()
        } catch (e) {
            console.error("Failed to parse request body:", e)
            return NextResponse.json({ error: "Invalid request body" }, { status: 400 })
        }

        try {
            const response = await fetch("https://api.evict.bot/roles/apply", {  
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${session.user.userToken}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    role_id: body.role_id,
                    display_name: body.display_name,
                    description: body.description,
                    discord_id: body.discord_id,
                    email: body.email
                })
            })

            if (!response.ok) {
                const errorData = await response.text()
                console.error("API Error response:", errorData)
                return NextResponse.json({ 
                    error: "Failed to submit application" 
                }, { status: response.status })
            }

            return NextResponse.json({ success: true })
        } catch (e) {
            console.error("API request failed:", e)
            return NextResponse.json({ error: "Failed to contact API" }, { status: 500 })
        }
    } catch (error) {
        console.error("Beta request error:", error)
        return NextResponse.json({ error: "Internal server error" }, { status: 500 })
    }
}