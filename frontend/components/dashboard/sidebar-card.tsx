"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { fadeSlideUp } from "@/lib/motion";

export default function SidebarCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle?: string;
}) {
  return (
    <motion.div
      variants={fadeSlideUp}
      whileHover={{ y: -2, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      <Card className="cursor-pointer transition-shadow hover:shadow-lg">
        <CardContent className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-semibold">{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
