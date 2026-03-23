"use client";

import { motion } from "framer-motion";
import SidebarCard from "./sidebar-card";
import { staggerContainer } from "@/lib/motion";

export default function RightSidebar({ role }: { role: "brand" | "influencer" }) {
  return (
    <motion.aside
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
      className="hidden xl:block w-80 border-l bg-background p-4 space-y-4"
    >
      {role === "brand" && (
        <>
          <SidebarCard title="Active Campaigns" value="4" subtitle="Running" />
          <SidebarCard
            title="Pending Approvals"
            value="7"
            subtitle="Waiting"
          />
        </>
      )}

      {role === "influencer" && (
        <>
          <SidebarCard
            title="New Campaigns"
            value="3"
            subtitle="Matched"
          />
          <SidebarCard
            title="Earnings"
            value="₹24,500"
            subtitle="This month"
          />
        </>
      )}

      <SidebarCard title="Notifications" value="5" subtitle="Unread" />
    </motion.aside>
  );
}
