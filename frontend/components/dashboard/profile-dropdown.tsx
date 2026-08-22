"use client";

import { useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { LogOut, User } from "lucide-react";
import { logout } from "../../lib/auth";

interface Props {
  user: {
    /**
     * Optional: `GET /users/me` returns only {id, email, role}, so this is
     * usually absent. It used to be typed as required, and the component
     * rendered a blank line for every user because the value was undefined.
     */
    name?: string;
    email: string;
    role?: string;
    avatarUrl?: string;
  };
}

export default function ProfileDropdown({ user }: Props) {
  const router = useRouter();


  async function handleLogout() {
    try {
      await logout()
    } finally {
      router.replace("/login")
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <Avatar className="h-9 w-9 cursor-pointer">
          <AvatarImage src={user.avatarUrl} />
          <AvatarFallback>
            {(user.name || user.email)?.charAt(0)?.toUpperCase() ?? "U"}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <p className="text-sm font-medium">{user.name || user.email}</p>
          {user.name && (
            <p className="text-xs text-muted-foreground">{user.email}</p>
          )}
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={() => router.push(
          user.role === "ADMIN" ? "/dashboard/admin" : user.role === "BRAND" ? "/dashboard/brand-profile" : "/dashboard/profile"
        )}>
          <User className="mr-2 h-4 w-4" />
          {user.role === "ADMIN" ? "Admin Console" : "Profile"}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={handleLogout}
          className="text-red-500 focus:text-red-500"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
