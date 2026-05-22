import type React from "react"
import Navigation from "@/components/navigation"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen bg-gray-100">
      <Navigation />
      <div className="flex-1 md:ml-64">
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}
