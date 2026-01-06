import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";


import ScrollToTop from "./components/ui/ScrollToTop";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap"
});

export const metadata: Metadata = {
  title: "AstraGuard AI - Mission Control",
  description: "Satellite security and mission control dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} antialiased`}
      >
        {children}
        <ScrollToTop />
      </body>
    </html>
  );
}
