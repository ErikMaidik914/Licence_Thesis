"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/auth-context"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, Award, LineChart, Calendar, Camera, Bell } from "lucide-react"
import Link from "next/link"
import apiClient from "@/lib/api-client"

interface Scan {
  id: string
  equipment: string
  detected_at: string
}

interface UserProfile {
  id: string
  username: string
  is_active: boolean
  scans: Scan[]
  by_muscle: Record<string, Scan[]>
}

export default function DashboardPage() {
  const { user, token, hasScope } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token) {
      apiClient.setToken(token)
      fetchUserProfile()
    }
  }, [token])

  const fetchUserProfile = async () => {
    try {
      setIsLoading(true)
      const data = await apiClient.getUserProfile()
      setProfile(data as UserProfile)
    } catch (err) {
      setError("Failed to load profile data")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>

        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <Card>
            <CardContent className="p-6">
              <p className="text-red-500">{error}</p>
              <Button onClick={fetchUserProfile} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Welcome, {user?.username}!</CardTitle>
                <CardDescription>Here&apos;s an overview of your fitness journey</CardDescription>
              </CardHeader>
              <CardContent>
                {profile && (
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium">Recent Equipment Scans</h3>
                      {profile.scans && profile.scans.length > 0 ? (
                        <ul className="mt-2 space-y-1">
                          {profile.scans.slice(0, 3).map((scan) => (
                            <li key={scan.id} className="text-sm">
                              {scan.equipment} - {new Date(scan.detected_at).toLocaleDateString()}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-muted-foreground mt-2">No equipment scans yet</p>
                      )}
                    </div>

                    <div>
                      <h3 className="font-medium">Muscle Groups</h3>
                      {profile.by_muscle && Object.keys(profile.by_muscle).length > 0 ? (
                        <ul className="mt-2 space-y-1">
                          {Object.keys(profile.by_muscle).map((muscle) => (
                            <li key={muscle} className="text-sm">
                              {muscle}: {profile.by_muscle[muscle].length} scans
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-muted-foreground mt-2">No muscle data yet</p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {hasScope("progress") && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Progress Tracking</CardTitle>
                    <LineChart className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Track your fitness progress</p>
                    <Link href="/progress">
                      <Button className="w-full mt-4" size="sm">
                        View Progress
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              )}

              {hasScope("plans") && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Workout Plans</CardTitle>
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Manage your workout plans</p>
                    <Link href="/plans">
                      <Button className="w-full mt-4" size="sm">
                        View Plans
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              )}

              {hasScope("detect") && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Equipment Detection</CardTitle>
                    <Camera className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Detect gym equipment in photos</p>
                    <Link href="/detect">
                      <Button className="w-full mt-4" size="sm">
                        Detect Equipment
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              )}

              {hasScope("user") && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Badges</CardTitle>
                    <Award className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">View your achievement badges</p>
                    <Link href="/badges">
                      <Button className="w-full mt-4" size="sm">
                        View Badges
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              )}

              {hasScope("notifications") && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Notifications</CardTitle>
                    <Bell className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Manage your notifications</p>
                    <Link href="/notifications">
                      <Button className="w-full mt-4" size="sm">
                        View Notifications
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              )}
            </div>
          </>
        )}
      </div>
    </ProtectedRoute>
  )
}
