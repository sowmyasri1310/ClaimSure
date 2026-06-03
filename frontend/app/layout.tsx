import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const outfit = Outfit({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ClaimSure — AI Medical Claims Dispute Resolver",
  description: "AI-powered Medical Insurance Claim Dispute Resolver with Healthcare Triage. Analyze hospital bills, doctor reports and policies.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.className} bg-slate-50 min-h-screen flex flex-col text-slate-800 antialiased`}>
        <Navbar />
        <main className="flex-grow">
          {children}
        </main>
      </body>
    </html>
  );
}
