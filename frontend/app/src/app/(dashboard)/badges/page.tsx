"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/auth-context"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, Award } from "lucide-react"
import apiClient from "@/lib/api-client"

interface Badge {
  id: string
  badge_id: string
  user_id: string
  awarded_at: string
}

export default function BadgesPage() {
  const { token } = useAuth()
  const [badges, setBadges] = useState<Badge[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token) {
      apiClient.setToken(token)
      fetchBadges()
    }
  }, [token])

  const fetchBadges = async () => {
    try {
      setIsLoading(true)
      const data = (await apiClient.getUserBadges()) as Badge[]
      setBadges(data)
    } catch (err) {
      setError("Failed to load badges")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleEvaluateBadges = async () => {
    try {
      setIsEvaluating(true)
      const newBadges = (await apiClient.evaluateBadges()) as Badge[]
      setBadges((prevBadges) => {
        // Combine existing badges with new ones, avoiding duplicates
        const badgeIds = new Set(prevBadges.map((b) => b.id))
        const uniqueNewBadges = newBadges.filter((b) => !badgeIds.has(b.id))
        return [...prevBadges, ...uniqueNewBadges]
      })
    } catch (err) {
      setError("Failed to evaluate badges")
      console.error(err)
    } finally {
      setIsEvaluating(false)
    }
  }

  return (
    <ProtectedRoute requiredScope="user">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Your Badges</h1>
          <Button onClick={handleEvaluateBadges} disabled={isEvaluating}>
            {isEvaluating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Evaluating...
              </>
            ) : (
              <>
                <Award className="mr-2 h-4 w-4" />
                Evaluate Badges
              </>
            )}
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : badges.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-8">
              <Award className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-xl font-medium">No Badges Yet</h3>
              <p className="text-center text-muted-foreground mt-2">Continue your fitness journey to earn badges!</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {badges.map((badge) => (
              <Card key={badge.id}>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Award className="h-5 w-5 mr-2 text-yellow-500" />
                    {badge.badge_id}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Awarded on {new Date(badge.awarded_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  )
}
