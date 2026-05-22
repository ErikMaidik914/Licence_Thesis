/* eslint-disable @typescript-eslint/no-unused-vars */
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
import { Loader2, Bell, Send, Check } from "lucide-react"
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
import { Textarea } from "@/components/ui/textarea"
import apiClient from "@/lib/api-client"


interface Notification {
  id: string
  user_id: string
  type: string
  payload: unknown
  sent_at: string
  status: string
}

export default function NotificationsPage() {
  const { token } = useAuth()
  const [isRegisterDialogOpen, setIsRegisterDialogOpen] = useState(false)
  const [isSendDialogOpen, setIsSendDialogOpen] = useState(false)
  const [deviceToken, setDeviceToken] = useState("")
  const [platform, setPlatform] = useState("ios")
  const [notificationType, setNotificationType] = useState("reminder")
  const [notificationMessage, setNotificationMessage] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token) {
      apiClient.setToken(token)
      // In a real app, we would fetch notifications here
      // For this demo, we'll use mock data
      setNotifications([
        {
          id: "1",
          user_id: "user123",
          type: "reminder",
          payload: { message: "Time for your workout!" },
          sent_at: new Date().toISOString(),
          status: "delivered",
        },
        {
          id: "2",
          user_id: "user123",
          type: "achievement",
          payload: { message: "You earned a new badge!", badge: "Consistent Workout" },
          sent_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
          status: "delivered",
        },
      ])
    }
  }, [token])

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!deviceToken) {
      setFormError("Device token is required")
      return
    }

    setIsSubmitting(true)

    try {
      await apiClient.registerDevice(deviceToken, platform)

      // Reset form and close dialog
      setDeviceToken("")
      setPlatform("ios")
      setIsRegisterDialogOpen(false)
    } catch (err) {
      setFormError("Failed to register device")
      console.error(err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSendNotification = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!notificationMessage) {
      setFormError("Message is required")
      return
    }

    setIsSubmitting(true)

    try {
      const payload = { message: notificationMessage }
      await apiClient.sendNotification(payload, notificationType)

      // Add to local notifications list
      const newNotification = {
        id: Date.now().toString(),
        user_id: "user123",
        type: notificationType,
        payload,
        sent_at: new Date().toISOString(),
        status: "sent",
      }

      setNotifications((prev) => [newNotification, ...prev])

      // Reset form and close dialog
      setNotificationMessage("")
      setNotificationType("reminder")
      setIsSendDialogOpen(false)
    } catch (err) {
      setFormError("Failed to send notification")
      console.error(err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleAcknowledge = async (notificationId: string) => {
    try {
      await apiClient.acknowledgeNotification(notificationId)

      // Update local state
      setNotifications((prev) =>
        prev.map((notif) => (notif.id === notificationId ? { ...notif, status: "acknowledged" } : notif)),
      )
    } catch (err) {
      console.error("Failed to acknowledge notification:", err)
    }
  }

  return (
    <ProtectedRoute requiredScope="notifications">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Notifications</h1>
          <div className="flex gap-2">
            <Dialog open={isRegisterDialogOpen} onOpenChange={setIsRegisterDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">Register Device</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Register Device</DialogTitle>
                  <DialogDescription>Register a device to receive push notifications.</DialogDescription>
                </DialogHeader>

                <form onSubmit={handleRegisterDevice} className="space-y-4 mt-4">
                  {formError && (
                    <Alert variant="destructive">
                      <AlertDescription>{formError}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="deviceToken">Device Token</Label>
                    <Input
                      id="deviceToken"
                      value={deviceToken}
                      onChange={(e) => setDeviceToken(e.target.value)}
                      placeholder="Enter device token"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="platform">Platform</Label>
                    <Select value={platform} onValueChange={setPlatform}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ios">iOS</SelectItem>
                        <SelectItem value="android">Android</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <DialogFooter>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Registering...
                        </>
                      ) : (
                        "Register Device"
                      )}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            <Dialog open={isSendDialogOpen} onOpenChange={setIsSendDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Send className="h-4 w-4 mr-2" />
                  Send Notification
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Send Notification</DialogTitle>
                  <DialogDescription>Send a notification to your registered devices.</DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSendNotification} className="space-y-4 mt-4">
                  {formError && (
                    <Alert variant="destructive">
                      <AlertDescription>{formError}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="notificationType">Notification Type</Label>
                    <Select value={notificationType} onValueChange={setNotificationType}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="reminder">Reminder</SelectItem>
                        <SelectItem value="achievement">Achievement</SelectItem>
                        <SelectItem value="alert">Alert</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notificationMessage">Message</Label>
                    <Textarea
                      id="notificationMessage"
                      value={notificationMessage}
                      onChange={(e) => setNotificationMessage(e.target.value)}
                      placeholder="Enter notification message"
                      required
                    />
                  </div>

                  <DialogFooter>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        "Send Notification"
                      )}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Your Notifications</CardTitle>
            <CardDescription>View and manage your notifications</CardDescription>
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
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Bell className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-center text-muted-foreground">No notifications yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {notifications.map((notification) => (
                  <Card key={notification.id}>
                    <CardHeader className="py-3 px-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-base capitalize">{notification.type}</CardTitle>
                          <CardDescription>{new Date(notification.sent_at).toLocaleString()}</CardDescription>
                        </div>
                        {notification.status !== "acknowledged" && (
                          <Button variant="ghost" size="sm" onClick={() => handleAcknowledge(notification.id)}>
                            <Check className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="py-2 px-4">
                      <p>{(notification.payload as { message: string }).message}</p>
                      {(notification.payload as { message: string; badge?: string }).badge && (
                        <p className="mt-2 text-sm">
                          <span className="font-medium">Badge:</span> {(notification.payload as { message: string; badge?: string }).badge}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
