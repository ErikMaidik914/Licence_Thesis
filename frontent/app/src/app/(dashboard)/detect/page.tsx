"use client"

import type React from "react"

import { useState, useRef } from "react"
import { useAuth } from "@/context/auth-context"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, Upload, Camera } from "lucide-react"
import apiClient from "@/lib/api-client"

interface DetectionResult {
  name: string
  score: number
  box: {
    x1: number
    y1: number
    x2: number
    y2: number
  }
}

export default function DetectPage() {
  const { token } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [results, setResults] = useState<DetectionResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]

      // Check file type
      if (!selectedFile.type.match("image/jpeg|image/png|image/bmp")) {
        setError("Please select a JPEG, PNG, or BMP image")
        return
      }

      // Check file size (5MB max)
      if (selectedFile.size > 5 * 1024 * 1024) {
        setError("Image size must be less than 5MB")
        return
      }

      setFile(selectedFile)
      setError(null)
      setResults([])

      // Create preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setPreview(e.target?.result as string)
      }
      reader.readAsDataURL(selectedFile)
    }
  }

  const handleDetect = async () => {
    if (!file || !token) return

    setIsLoading(true)
    setError(null)

    try {
      apiClient.setToken(token)
      const detectionResults = await apiClient.detectEquipment(file) as DetectionResult[]
      setResults(detectionResults)

      // Draw bounding boxes on canvas
      if (detectionResults.length > 0 && preview && canvasRef.current) {
        drawBoundingBoxes(detectionResults)
      }
    } catch (err) {
      setError("Detection failed. Please try again.")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const drawBoundingBoxes = (detections: DetectionResult[]) => {
    const canvas = canvasRef.current
    if (!canvas || !preview) return

    const img = new Image()
    img.crossOrigin = "anonymous"
    img.onload = () => {
      // Set canvas dimensions to match image
      canvas.width = img.width
      canvas.height = img.height

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      // Draw the image
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

      // Draw bounding boxes
      detections.forEach((detection) => {
        const { x1, y1, x2, y2 } = detection.box
        const width = x2 - x1
        const height = y2 - y1

        // Draw rectangle
        ctx.strokeStyle = "red"
        ctx.lineWidth = 3
        ctx.strokeRect(x1, y1, width, height)

        // Draw label background
        const label = `${detection.name} (${Math.round(detection.score * 100)}%)`
        const textMetrics = ctx.measureText(label)
        const textHeight = 20
        ctx.fillStyle = "rgba(255, 0, 0, 0.7)"
        ctx.fillRect(x1, y1 - textHeight, textMetrics.width + 10, textHeight)

        // Draw label text
        ctx.fillStyle = "white"
        ctx.font = "14px Arial"
        ctx.fillText(label, x1 + 5, y1 - 5)
      })
    }
    img.src = preview
  }

  const resetDetection = () => {
    setFile(null)
    setPreview(null)
    setResults([])
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <ProtectedRoute requiredScope="detect">
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Equipment Detection</h1>

        <Card>
          <CardHeader>
            <CardTitle>Detect Gym Equipment</CardTitle>
            <CardDescription>Upload an image to detect gym equipment using AI</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/bmp"
                  onChange={handleFileChange}
                  className="max-w-sm"
                />
                <Button onClick={handleDetect} disabled={!file || isLoading}>
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Detecting...
                    </>
                  ) : (
                    <>
                      <Camera className="mr-2 h-4 w-4" />
                      Detect
                    </>
                  )}
                </Button>
                {(file || results.length > 0) && (
                  <Button variant="outline" onClick={resetDetection}>
                    Reset
                  </Button>
                )}
              </div>

              {preview && (
                <div className="mt-6 border rounded-md p-4">
                  <h3 className="text-lg font-medium mb-2">Detection Results</h3>

                  <div className="relative">
                    <canvas ref={canvasRef} className="max-w-full h-auto border rounded" />

                    {results.length === 0 && !isLoading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-white">
                        <p>Click &quot;Detect&quot; to analyze this image</p>
                      </div>
                    )}
                  </div>

                  {results.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-medium mb-2">Detected Equipment:</h4>
                      <ul className="space-y-1">
                        {results.map((result, index) => (
                          <li key={index} className="flex items-center">
                            <span className="w-4 h-4 bg-red-500 mr-2"></span>
                            {result.name} - {Math.round(result.score * 100)}% confidence
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {!preview && (
                <div className="border border-dashed rounded-md p-8 flex flex-col items-center justify-center text-center">
                  <Upload className="h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium">Upload an Image</h3>
                  <p className="text-sm text-muted-foreground mt-1">Upload a JPEG, PNG, or BMP image (max 5MB)</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
