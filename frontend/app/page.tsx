"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useIsAuthenticated } from "@/lib/store/auth";
import LandingNav from "@/components/landing/LandingNav";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import Features from "@/components/landing/Features";
import DataOwnership from "@/components/landing/DataOwnership";
import ClosingCta from "@/components/landing/ClosingCta";
import Footer from "@/components/landing/Footer";

export default function RootPage() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();

  // Signed-in users skip the marketing page and go straight to the app.
  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, router]);

  if (isAuthenticated) return null;

  return (
    <div className="flex min-h-full flex-col bg-paper">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <HowItWorks />
        <Features />
        <DataOwnership />
        <ClosingCta />
      </main>
      <Footer />
    </div>
  );
}
