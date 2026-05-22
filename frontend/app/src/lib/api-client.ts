/* eslint-disable @typescript-eslint/no-explicit-any */
type RequestOptions = {
  method?: string
  headers?: Record<string, string>
  body?: any
  isFormData?: boolean
}

class ApiClient {
  private baseUrl: string
  private token: string | null

  constructor(baseUrl = "", token: string | null = null) {
    this.baseUrl = baseUrl
    this.token = token
  }

  setToken(token: string | null) {
    this.token = token
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", headers = {}, body, isFormData = false } = options

    const url = `${this.baseUrl}${endpoint}`

    const requestHeaders: Record<string, string> = {
      ...headers,
    }

    // Add authorization header if token exists
    if (this.token) {
      requestHeaders["Authorization"] = `Bearer ${this.token}`
    }

    // Set content type if not form data
    if (!isFormData && method !== "GET" && !requestHeaders["Content-Type"]) {
      requestHeaders["Content-Type"] = "application/json"
    }

    const requestOptions: RequestInit = {
      method,
      headers: requestHeaders,
    }

    // Add body if it exists
    if (body) {
      if (isFormData) {
        requestOptions.body = body
      } else if (body instanceof FormData) {
        requestOptions.body = body
        // Don't set Content-Type for FormData, browser will set it with boundary
        delete requestHeaders["Content-Type"]
      } else {
        requestOptions.body = JSON.stringify(body)
      }
    }

    try {
      const response = await fetch(url, requestOptions)

      // Handle no content responses (204)
      if (response.status === 204) {
        return {} as T
      }

      // For non-JSON responses
      if (!response.headers.get("content-type")?.includes("application/json")) {
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }
        return {} as T
      }

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "API request failed")
      }

      return data as T
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Auth endpoints
  async login(username: string, password: string) {
    const formData = new URLSearchParams()
    formData.append("username", username)
    formData.append("password", password)

    return this.request<{ access_token: string; token_type: string }>("/api/v1/auth/login", {
      method: "POST",
      body: formData,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      isFormData: true,
    })
  }

  async register(username: string, email: string, password: string) {
    return this.request("/api/v1/auth/register", {
      method: "POST",
      body: { username, email, password },
    })
  }

  // User profile
  async getUserProfile() {
    return this.request("/api/v1/users/profile")
  }

  // Progress endpoints
  async getProgressEntries(
    params: { start?: string; end?: string; muscle_group?: string; skip?: number; limit?: number } = {},
  ) {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, value.toString())
      }
    })

    return this.request(`/api/v1/progress?${queryParams.toString()}`)
  }

  async logProgressEntry(data: { muscle_group: string; metric: string; value: number; date?: string; metadata?: any }) {
    return this.request("/api/v1/progress", {
      method: "POST",
      body: data,
    })
  }

  async getProgressTrends(
    params: { period?: "day" | "week" | "month"; from?: string; to?: string; muscle_group?: string } = {},
  ) {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, value.toString())
      }
    })

    return this.request(`/api/v1/progress/trends?${queryParams.toString()}`)
  }

  // Workout plans endpoints
  async createWorkoutPlan(data: { name: string; goal: string; start_date: string; end_date?: string; metadata?: any }) {
    return this.request("/api/v1/plans", {
      method: "POST",
      body: data,
    })
  }

  async getActivePlan() {
    return this.request("/api/v1/plans/active")
  }

  async getPlanHistory(skip = 0, limit = 50) {
    return this.request(`/api/v1/plans/history?skip=${skip}&limit=${limit}`)
  }

  async updatePlan(
    planId: string,
    updates: { name?: string; goal?: string; start_date?: string; end_date?: string; metadata?: any },
  ) {
    return this.request(`/api/v1/plans/${planId}`, {
      method: "PUT",
      body: updates,
    })
  }

  // Equipment detection
  async detectEquipment(file: File) {
    const formData = new FormData()
    formData.append("file", file)

    return this.request("/api/v1/detect", {
      method: "POST",
      body: formData,
    })
  }

  // Badges
  async evaluateBadges() {
    return this.request("/api/v1/badges/evaluate", {
      method: "POST",
    })
  }

  async getUserBadges() {
    return this.request("/api/v1/badges")
  }

  // Notifications
  async registerDevice(deviceToken: string, platform: string) {
    return this.request("/api/v1/notifications/register-device", {
      method: "POST",
      body: { device_token: deviceToken, platform },
    })
  }

  async sendNotification(payload: any, notifType: string) {
    return this.request("/api/v1/notifications/send", {
      method: "POST",
      body: { payload, notif_type: notifType },
    })
  }

  async acknowledgeNotification(notificationId: string) {
    return this.request(`/api/v1/notifications/${notificationId}/ack`, {
      method: "POST",
    })
  }

  // Admin endpoints (requires admin role)
  async listUsers(skip = 0, limit = 100) {
    return this.request(`/api/v1/admin/users?skip=${skip}&limit=${limit}`)
  }

  async getUser(userId: string) {
    return this.request(`/api/v1/admin/users/${userId}`)
  }

  async deleteUser(userId: string) {
    return this.request(`/api/v1/admin/users/${userId}`, {
      method: "DELETE",
    })
  }

  async getStats(since?: string) {
    const query = since ? `?since=${since}` : ""
    return this.request(`/api/v1/admin/stats${query}`)
  }
}

// Create a singleton instance
const apiClient = new ApiClient()

export default apiClient
