/* eslint-disable @typescript-eslint/no-unused-vars */
"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/auth-context"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Plus, Calendar } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import apiClient from "@/lib/api-client"

interface PlanPhase {
  id: string
  phase_name: string
  week_number: number
  details: unknown
}

interface WorkoutPlan {
  id: string
  name: string
  goal: string
  start_date: string
  end_date?: string
  metadata?: unknown
  phases: PlanPhase[]
}

export default function PlansPage() {
  const { token } = useAuth()
  const [activePlan, setActivePlan] = useState<WorkoutPlan | null>(null)
  const [planHistory, setPlanHistory] = useState<WorkoutPlan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Form state
  const [planName, setPlanName] = useState("")
  const [planGoal, setPlanGoal] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (token) {
      apiClient.setToken(token)
      fetchActivePlan()
      fetchPlanHistory()
    }
  }, [token])

  const fetchActivePlan = async () => {
    try {
      const data = await apiClient.getActivePlan()
      setActivePlan(data as WorkoutPlan)
    } catch (err) {
      // It's okay if there's no active plan
      console.log("No active plan found")
    }
  }

  const fetchPlanHistory = async () => {
    try {
      setIsLoading(true)
      const data = await apiClient.getPlanHistory()
      setPlanHistory(data as WorkoutPlan[])
    } catch (err) {
      setError("Failed to load workout plans")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!planName || !planGoal || !startDate) {
      setFormError("Name, goal, and start date are required")
      return
    }

    setIsSubmitting(true)

    try {
      const planData = {
        name: planName,
        goal: planGoal,
        start_date: startDate,
        end_date: endDate || undefined,
      }

      await apiClient.createWorkoutPlan(planData)

      // Reset form and close dialog
      setPlanName("")
      setPlanGoal("")
      setStartDate("")
      setEndDate("")
      setIsDialogOpen(false)

      // Refresh data
      fetchActivePlan()
      fetchPlanHistory()
    } catch (err) {
      setFormError("Failed to create workout plan")
      console.error(err)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <ProtectedRoute requiredScope="plans">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Workout Plans</h1>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Plan
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Workout Plan</DialogTitle>
                <DialogDescription>Create a new workout plan to track your fitness goals.</DialogDescription>
              </DialogHeader>

              <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                {formError && (
                  <Alert variant="destructive">
                    <AlertDescription>{formError}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="planName">Plan Name</Label>
                  <Input
                    id="planName"
                    value={planName}
                    onChange={(e) => setPlanName(e.target.value)}
                    placeholder="e.g., Summer Strength Training"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="planGoal">Goal</Label>
                  <Input
                    id="planGoal"
                    value={planGoal}
                    onChange={(e) => setPlanGoal(e.target.value)}
                    placeholder="e.g., Build muscle, Lose weight"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="startDate">Start Date</Label>
                  <Input
                    id="startDate"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="endDate">End Date (Optional)</Label>
                  <Input id="endDate" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                </div>

                <DialogFooter>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      "Create Plan"
                    )}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Tabs defaultValue="active">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="active">Active Plan</TabsTrigger>
            <TabsTrigger value="history">Plan History</TabsTrigger>
          </TabsList>

          <TabsContent value="active">
            {activePlan ? (
              <Card>
                <CardHeader>
                  <CardTitle>{activePlan.name}</CardTitle>
                  <CardDescription>Goal: {activePlan.goal}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h3 className="text-sm font-medium">Start Date</h3>
                        <p>{new Date(activePlan.start_date).toLocaleDateString()}</p>
                      </div>
                      {activePlan.end_date && (
                        <div>
                          <h3 className="text-sm font-medium">End Date</h3>
                          <p>{new Date(activePlan.end_date).toLocaleDateString()}</p>
                        </div>
                      )}
                    </div>

                    <div>
                      <h3 className="text-sm font-medium mb-2">Phases</h3>
                      {activePlan.phases.length > 0 ? (
                        <div className="space-y-2">
                          {activePlan.phases.map((phase) => (
                            <Card key={phase.id}>
                              <CardHeader className="py-2 px-4">
                                <CardTitle className="text-sm">
                                  Week {phase.week_number}: {phase.phase_name}
                                </CardTitle>
                              </CardHeader>
                              <CardContent className="py-2 px-4">
                                <pre className="text-xs whitespace-pre-wrap">
                                  {JSON.stringify(phase.details, null, 2)}
                                </pre>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No phases defined yet</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center justify-center p-8">
                  <Calendar className="h-16 w-16 text-muted-foreground mb-4" />
                  <h3 className="text-xl font-medium">No Active Plan</h3>
                  <p className="text-center text-muted-foreground mt-2">Create a new workout plan to get started</p>
                  <Button className="mt-4" onClick={() => setIsDialogOpen(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Plan
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="history">
            <Card>
              <CardHeader>
                <CardTitle>Plan History</CardTitle>
                <CardDescription>View your previous workout plans</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex justify-center p-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                ) : error ? (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ) : planHistory.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No workout plan history found</p>
                ) : (
                  <div className="space-y-4">
                    {planHistory.map((plan) => (
                      <Card key={plan.id}>
                        <CardHeader className="py-3 px-4">
                          <CardTitle className="text-lg">{plan.name}</CardTitle>
                          <CardDescription>Goal: {plan.goal}</CardDescription>
                        </CardHeader>
                        <CardContent className="py-2 px-4">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="font-medium">Start Date:</span>{" "}
                              {new Date(plan.start_date).toLocaleDateString()}
                            </div>
                            {plan.end_date && (
                              <div>
                                <span className="font-medium">End Date:</span>{" "}
                                {new Date(plan.end_date).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        </CardContent>
                        <CardFooter className="py-2 px-4 border-t">
                          <p className="text-xs text-muted-foreground">{plan.phases.length} phases</p>
                        </CardFooter>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ProtectedRoute>
  )
}
