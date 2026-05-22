/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/auth-context"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Plus, LineChart } from "lucide-react"
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

interface ProgressEntry {
  id: string
  date: string
  muscle_group: string
  metric: string
  value: number
  metadata?: unknown
}

interface TrendData {
  period: string
  entries: number
  total: number
}

export default function ProgressPage() {
  const { token } = useAuth()
  const [entries, setEntries] = useState<ProgressEntry[]>([])
  const [trends, setTrends] = useState<TrendData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Form state
  const [muscleGroup, setMuscleGroup] = useState("")
  const [metric, setMetric] = useState("")
  const [value, setValue] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Filter state
  const [filterMuscleGroup, setFilterMuscleGroup] = useState("")
  const [period, setPeriod] = useState("week")

  useEffect(() => {
    if (token) {
      apiClient.setToken(token)
      fetchProgressEntries()
      fetchTrends()
    }
  }, [token, filterMuscleGroup])

  const fetchProgressEntries = async () => {
    try {
      setIsLoading(true)
      const params: any = { limit: 100 }
      if (filterMuscleGroup) {
        params.muscle_group = filterMuscleGroup
      }
      const data = await apiClient.getProgressEntries(params)
      setEntries(data as ProgressEntry[])
    } catch (err) {
      setError("Failed to load progress entries")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchTrends = async () => {
    try {
      const params: any = { period }
      if (filterMuscleGroup) {
        params.muscle_group = filterMuscleGroup
      }
      const data = await apiClient.getProgressTrends(params)
      setTrends(data as TrendData[])
    } catch (err) {
      console.error("Failed to load trends:", err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!muscleGroup || !metric || !value) {
      setFormError("All fields are required")
      return
    }

    const numValue = Number.parseFloat(value)
    if (isNaN(numValue)) {
      setFormError("Value must be a number")
      return
    }

    setIsSubmitting(true)

    try {
      await apiClient.logProgressEntry({
        muscle_group: muscleGroup,
        metric,
        value: numValue,
        date: new Date().toISOString(),
      })

      // Reset form and close dialog
      setMuscleGroup("")
      setMetric("")
      setValue("")
      setIsDialogOpen(false)

      // Refresh data
      fetchProgressEntries()
      fetchTrends()
    } catch (err) {
      setFormError("Failed to log progress entry")
      console.error(err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod)
    // Fetch trends with new period
    fetchTrends()
  }

  return (
    <ProtectedRoute requiredScope="progress">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Progress Tracking</h1>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Log Progress
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Log Progress Entry</DialogTitle>
                <DialogDescription>Record your fitness progress for tracking and analysis.</DialogDescription>
              </DialogHeader>

              <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                {formError && (
                  <Alert variant="destructive">
                    <AlertDescription>{formError}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="muscleGroup">Muscle Group</Label>
                  <Select value={muscleGroup} onValueChange={setMuscleGroup} required>
                    <SelectTrigger>
                      <SelectValue placeholder="Select muscle group" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="chest">Chest</SelectItem>
                      <SelectItem value="back">Back</SelectItem>
                      <SelectItem value="legs">Legs</SelectItem>
                      <SelectItem value="shoulders">Shoulders</SelectItem>
                      <SelectItem value="arms">Arms</SelectItem>
                      <SelectItem value="core">Core</SelectItem>
                      <SelectItem value="cardio">Cardio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="metric">Metric</Label>
                  <Input
                    id="metric"
                    value={metric}
                    onChange={(e) => setMetric(e.target.value)}
                    placeholder="e.g., bench_press, squat, run_distance"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="value">Value</Label>
                  <Input
                    id="value"
                    type="number"
                    step="0.01"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder="e.g., 100 (lbs), 10 (km)"
                    required
                  />
                </div>

                <DialogFooter>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      "Save Entry"
                    )}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Filter Options</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="w-full sm:w-1/2">
                  <Label htmlFor="filterMuscleGroup">Muscle Group</Label>
                  <Select value={filterMuscleGroup} onValueChange={setFilterMuscleGroup}>
                    <SelectTrigger>
                      <SelectValue placeholder="All muscle groups" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All muscle groups</SelectItem>
                      <SelectItem value="chest">Chest</SelectItem>
                      <SelectItem value="back">Back</SelectItem>
                      <SelectItem value="legs">Legs</SelectItem>
                      <SelectItem value="shoulders">Shoulders</SelectItem>
                      <SelectItem value="arms">Arms</SelectItem>
                      <SelectItem value="core">Core</SelectItem>
                      <SelectItem value="cardio">Cardio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="entries">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="entries">Progress Entries</TabsTrigger>
              <TabsTrigger value="trends">Trends</TabsTrigger>
            </TabsList>

            <TabsContent value="entries">
              <Card>
                <CardHeader>
                  <CardTitle>Progress Entries</CardTitle>
                  <CardDescription>View your logged progress entries</CardDescription>
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
                  ) : entries.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      No progress entries found. Start logging your progress!
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2 px-4">Date</th>
                            <th className="text-left py-2 px-4">Muscle Group</th>
                            <th className="text-left py-2 px-4">Metric</th>
                            <th className="text-left py-2 px-4">Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {entries.map((entry) => (
                            <tr key={entry.id} className="border-b">
                              <td className="py-2 px-4">{new Date(entry.date).toLocaleDateString()}</td>
                              <td className="py-2 px-4 capitalize">{entry.muscle_group}</td>
                              <td className="py-2 px-4">{entry.metric}</td>
                              <td className="py-2 px-4">{entry.value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="trends">
              <Card>
                <CardHeader>
                  <CardTitle>Progress Trends</CardTitle>
                  <CardDescription>Analyze your progress over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    <Label>Time Period</Label>
                    <div className="flex space-x-2 mt-2">
                      <Button
                        variant={period === "day" ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePeriodChange("day")}
                      >
                        Daily
                      </Button>
                      <Button
                        variant={period === "week" ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePeriodChange("week")}
                      >
                        Weekly
                      </Button>
                      <Button
                        variant={period === "month" ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePeriodChange("month")}
                      >
                        Monthly
                      </Button>
                    </div>
                  </div>

                  {trends.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8">
                      <LineChart className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-center text-muted-foreground">
                        Not enough data to show trends. Keep logging your progress!
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2 px-4">Period</th>
                            <th className="text-left py-2 px-4">Entries</th>
                            <th className="text-left py-2 px-4">Total</th>
                            <th className="text-left py-2 px-4">Average</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trends.map((trend, index) => (
                            <tr key={index} className="border-b">
                              <td className="py-2 px-4">{new Date(trend.period).toLocaleDateString()}</td>
                              <td className="py-2 px-4">{trend.entries}</td>
                              <td className="py-2 px-4">{trend.total.toFixed(2)}</td>
                              <td className="py-2 px-4">{(trend.total / trend.entries).toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </ProtectedRoute>
  )
}
