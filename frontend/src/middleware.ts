import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('nyaya_token')?.value;
  const { pathname } = request.nextUrl;

  // Define route guard rules
  const isProtectedPath = pathname.startsWith('/dashboard') || 
                          pathname.startsWith('/chat') || 
                          pathname.startsWith('/scan');

  const isAuthPath = pathname.startsWith('/signin');

  if (isProtectedPath && !token) {
    // Force sign-in redirect
    const signinUrl = new URL('/signin', request.url);
    return NextResponse.redirect(signinUrl);
  }

  if (isAuthPath && token) {
    // Redirect already authenticated users to dashboard
    const dashboardUrl = new URL('/dashboard', request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/chat/:path*',
    '/scan/:path*',
    '/signin'
  ],
};
