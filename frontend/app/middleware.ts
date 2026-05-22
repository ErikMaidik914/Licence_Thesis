import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value
  const isAuthPage = request.nextUrl.pathname.startsWith("/login") || request.nextUrl.pathname.startsWith("/register")

  // If trying to access auth page while logged in, redirect to dashboard
  if (isAuthPage && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  // If trying to access protected page without token, redirect to login
  if (!isAuthPage && !token && !request.nextUrl.pathname.startsWith("/api")) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("from", request.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    // Protected routes
    "/dashboard/:path*",
    "/progress/:path*",
    "/plans/:path*",
    "/detect/:path*",
    "/badges/:path*",
    "/notifications/:path*",
    "/admin/:path*",
    // Auth routes
    "/login",
    "/register",
  ],
}
