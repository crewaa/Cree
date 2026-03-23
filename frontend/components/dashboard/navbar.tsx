"use client";

import { motion } from "framer-motion";
import { fadeSlideUp } from "@/lib/motion";
import { ThemeToggle } from "./theme-toggle";
import ProfileDropdown from "./profile-dropdown";
import { useRouter } from "next/navigation";
import InstagramAnalytics from "./instagram-analytics";
import { useState } from "react";

export default function DashboardNavbar({ user }: any) {
  const router = useRouter();
  const [showInstagram, setShowInstagram] = useState(false)


  function handleLogoClick() {
    if (user.role === "BRAND") {
      router.push("/dashboard/brand");
    } else if (user.role === "INFLUENCER") {
      router.push("/dashboard/influencer");
    }
  }

  function handleDashboardClick() {
    if (user.role === "BRAND") {
      router.push("/dashboard/analytics/brand");
    } else if (user.role === "INFLUENCER") {
      router.push("/dashboard/analytics/influencer");
    }
  }

  // function handleDashboardClick() {
  //   setShowInstagram(prev => !prev)
  // }
  

  return (
    <motion.header
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
      className="sticky top-0 z-50 border-b bg-background"
    >
      <div className="flex h-16 items-center justify-between px-6">
        <div className="flex cursor-pointer items-center gap-2 hover:opacity-80 transition">
          <span className="text-xl font-semibold" onClick={handleLogoClick}>Crewaa</span>
          {/* <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize"> */}
            {/* {user.role} */}
            {/* Studio */}
          {/* </span> */}
        </div>

        <div className="flex items-center gap-4">
        <div>
      <div
        onClick={handleDashboardClick}
        className="cursor-pointer font-semibold"
      >
        Dashboard
      </div>

      {/* {showInstagram && (
  <div className="mt-6 animate-fade-in">
    <InstagramAnalytics userId={2} />
  </div>
)} */}
    </div>
          <ThemeToggle />
          <ProfileDropdown user={user} />
        </div>
      </div>
    </motion.header>
  );
}
