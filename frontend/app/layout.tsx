import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { REPO_URL } from "@/lib/config";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InsideMatch",
  description: "Live AI football companion built on synthetic match events.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        {children}
        <footer className="border-t border-white/10 px-4 py-4 text-center text-xs text-white/60">
          Synthetic match data. Clubs and players are fictional. Not affiliated with the Premier League. ·{" "}
          <a className="underline hover:text-white" href={REPO_URL}>Source</a>
        </footer>
      </body>
    </html>
  );
}
