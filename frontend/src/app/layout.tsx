import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/auth-context";
export const metadata: Metadata = { title: { default: "Adsyde", template: "%s · Adsyde" }, description: "Create compelling video ads with control." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AuthProvider>{children}</AuthProvider></body></html>; }
