"use client"

import { useAuth } from "@/context/auth-context"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Home, LineChart, Calendar, Camera, Award, Bell, Shield, LogOut, Menu, X } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

export default function Navigation() {
  const { user, logout, hasScope } = useAuth()
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)

  if (!user) return null

  const navItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: <Home className="h-5 w-5" />,
      active: pathname === "/dashboard",
      scope: null,
    },
    {
      name: "Progress",
      href: "/progress",
      icon: <LineChart className="h-5 w-5" />,
      active: pathname.startsWith("/progress"),
      scope: "progress",
    },
    {
      name: "Workout Plans",
      href: "/plans",
      icon: <Calendar className="h-5 w-5" />,
      active: pathname.startsWith("/plans"),
      scope: "plans",
    },
    {
      name: "Equipment Detection",
      href: "/detect",
      icon: <Camera className="h-5 w-5" />,
      active: pathname.startsWith("/detect"),
      scope: "detect",
    },
    {
      name: "Badges",
      href: "/badges",
      icon: <Award className="h-5 w-5" />,
      active: pathname.startsWith("/badges"),
      scope: "user",
    },
    {
      name: "Notifications",
      href: "/notifications",
      icon: <Bell className="h-5 w-5" />,
      active: pathname.startsWith("/notifications"),
      scope: "notifications",
    },
  ]

  // Add admin section if user has admin role
  if (user.scopes?.includes("admin")) {
    navItems.push({
      name: "Admin",
      href: "/admin",
      icon: <Shield className="h-5 w-5" />,
      active: pathname.startsWith("/admin"),
      scope: "admin",
    })
  }

  const toggleMenu = () => setIsOpen(!isOpen)

  return (
    <>
      {/* Mobile menu button */}
      <div className="md:hidden fixed top-4 right-4 z-50">
        <Button variant="outline" size="icon" onClick={toggleMenu}>
          {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {/* Navigation sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 bg-background border-r transform transition-transform duration-200 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div className="flex flex-col h-full">
          <div className="p-4 border-b">
            <h2 className="text-xl font-bold">Fitness App</h2>
            <p className="text-sm text-muted-foreground">Welcome, {user.username}</p>
          </div>

          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              // Skip items that require scopes the user doesn't have
              if (item.scope && !hasScope(item.scope)) return null

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    item.active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                  )}
                  onClick={() => setIsOpen(false)}
                >
                  {item.icon}
                  <span className="ml-3">{item.name}</span>
                </Link>
              )
            })}
          </nav>

          <div className="p-4 border-t">
            <Button variant="outline" className="w-full flex items-center justify-center" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}
