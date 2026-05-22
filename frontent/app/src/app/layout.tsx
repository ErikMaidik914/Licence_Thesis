import type React from "react"
import { Inter } from 'next/font/google'
import { AuthProvider } from "@/context/auth-context"
import { ThemeProvider } from "../components/theme-provider"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "Fitness App",
  description: "Track your fitness progress and workout plans",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}