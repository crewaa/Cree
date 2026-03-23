"use client";

import { motion } from "framer-motion";
import DashboardNavbar from "@/components/dashboard/navbar";
import RightSidebar from "@/components/dashboard/right-sidebar";
import { ThemeProvider } from "../../components/theme-provider";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "../../lib/user";

export default function DashboardLayout({ children }: any) {
 
  const [user, setUser] = useState<any>(null)
  const router = useRouter();

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await getCurrentUser();
        setUser(data);

        if(data.role === "BRAND" && !location.pathname.startsWith("/dashboard/brand")) {
          router.replace("/dashboard/brand");
        }

        if(data.role === "INFLUENCER" && !location.pathname.startsWith("/dashboard/influencer")) {
          router.replace("/dashboard/influencer");
        }
      } catch {
        router.replace("/login");
      }
    }
    loadUser();
  }, [router]);

  if (!user) return null;

  return (
    <ThemeProvider>
    <div className="min-h-screen">
      <DashboardNavbar user={user} />

      <div className="flex">
        <motion.main
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex-1 p-6"
        >
          {children}
        </motion.main>

        {/* <RightSidebar role={user?.role?.toUpperCase()} /> */}
      </div>
    </div>
    </ThemeProvider>
  );
}
