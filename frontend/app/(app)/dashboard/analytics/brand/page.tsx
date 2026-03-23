"use client";

import InstagramAnalytics from "../../../../../components/dashboard/instagram-analytics";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "../../../../../lib/user";


export default function Analytics() {

     const [user, setUser] = useState<any>(null)
      const router = useRouter();
    
      useEffect(() => {
        async function loadUser() {
          try {
            const data = await getCurrentUser();
            setUser(data);
    
            
          } catch {
            router.replace("/login");
          }
        }
        loadUser();
      }, [router]);
    
      if (!user) return null;

    return (
        <div>
            Brand Dashboard
        </div>
    )
}