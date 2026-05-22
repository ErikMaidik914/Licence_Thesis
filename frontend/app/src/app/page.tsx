"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/context/auth-context"
import { Loader2 } from "lucide-react"

export default function HomePage() {
  const router = useRouter()
  const { user, isLoading } = useAuth()

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        router.push("/dashboard")
      } else {
        router.push("/login")
      }
    }
  }, [user, isLoading, router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  )
}
