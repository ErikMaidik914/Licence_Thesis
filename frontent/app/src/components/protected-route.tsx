"use client"

import type React from "react"

import { useAuth } from "@/context/auth-context"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { Loader2 } from "lucide-react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredScope?: string
}

export default function ProtectedRoute({ children, requiredScope }: ProtectedRouteProps) {
  const { user, isLoading, hasScope } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login")
    }

    if (!isLoading && user && requiredScope && !hasScope(requiredScope)) {
      router.push("/dashboard")
    }
  }, [user, isLoading, router, requiredScope, hasScope])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (requiredScope && !hasScope(requiredScope)) {
    return null
  }

  return <>{children}</>
}
