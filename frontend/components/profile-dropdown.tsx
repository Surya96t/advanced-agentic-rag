"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Settings, CreditCard, LogOut, User, Moon, Sun } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useUser, useClerk } from "@clerk/nextjs";
import { useTheme } from "next-themes";
import { Switch } from "@/components/ui/switch";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Profile {
    name: string;
    email: string;
    avatar: string;
    subscription?: string;
}

interface MenuItem {
    label: string;
    value?: string;
    href: string;
    icon: React.ReactNode;
    external?: boolean;
}


interface ProfileDropdownProps extends React.HTMLAttributes<HTMLDivElement> {
    subscription?: string;
}

export default function ProfileDropdown({
    subscription = "Free",
    className,
    ...props
}: ProfileDropdownProps) {
    const { user } = useUser();
    const { signOut } = useClerk();
    const { resolvedTheme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);

    // Avoid hydration mismatch by only rendering theme-dependent UI after mount
    React.useEffect(() => {
        setMounted(true);
    }, []);

    // Use Clerk user data
    const profileData: Profile = {
        name: user?.fullName || "Loading...",
        email: user?.primaryEmailAddress?.emailAddress || "",
        avatar: user?.imageUrl || "https://api.dicebear.com/7.x/avataaars/svg?seed=default",
        subscription: subscription,
    };

    const menuItems: MenuItem[] = [
        {
            label: "Profile",
            href: "/profile",
            icon: <User className="w-4 h-4" />,
        },
        {
            label: "Subscription",
            value: profileData.subscription,
            href: "/subscription",
            icon: <CreditCard className="w-4 h-4" />,
        },
        {
            label: "Settings",
            href: "/settings",
            icon: <Settings className="w-4 h-4" />,
        },
    ];

    // Use resolvedTheme to handle "system" preference correctly
    const isDarkMode = resolvedTheme === "dark";
    
    const toggleTheme = () => {
        setTheme(isDarkMode ? "light" : "dark");
    };

    return (
        <div className={cn("relative", className)} {...props}>
            <DropdownMenu>
                <div className="group relative">
                    <DropdownMenuTrigger asChild>
                        <button
                            type="button"
                            className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <div className="relative">
                                <div className="w-8 h-8 rounded-full overflow-hidden border border-border">
                                    <Image
                                        src={profileData.avatar}
                                        alt={profileData.name}
                                        width={32}
                                        height={32}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            </div>
                            <div className="text-left hidden md:block">
                                <div className="text-sm font-medium leading-tight">
                                    {profileData.name}
                                </div>
                                <div className="text-xs text-muted-foreground leading-tight">
                                    {profileData.email}
                                </div>
                            </div>
                        </button>
                    </DropdownMenuTrigger>

                    <DropdownMenuContent
                        align="end"
                        sideOffset={4}
                        className="w-64 p-2 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm border border-zinc-200/60 dark:border-zinc-800/60 rounded-2xl shadow-xl shadow-zinc-900/5 dark:shadow-zinc-950/20 
                    data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-top-right"
                    >
                        <div className="space-y-1">
                            {menuItems.map((item) => (
                                <DropdownMenuItem key={item.label} asChild>
                                    <Link
                                        href={item.href}
                                        className="flex items-center p-3 hover:bg-zinc-100/80 dark:hover:bg-zinc-800/60 rounded-xl transition-all duration-200 cursor-pointer group hover:shadow-sm border border-transparent hover:border-zinc-200/50 dark:hover:border-zinc-700/50"
                                    >
                                        <div className="flex items-center gap-2 flex-1">
                                            {item.icon}
                                            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 tracking-tight leading-tight whitespace-nowrap group-hover:text-zinc-950 dark:group-hover:text-zinc-50 transition-colors">
                                                {item.label}
                                            </span>
                                        </div>
                                        <div className="shrink-0 ml-auto">
                                            {item.value && (
                                                <span className="text-xs font-medium rounded-md py-1 px-2 tracking-tight text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-purple-500/10 border border-purple-500/10">
                                                    {item.value}
                                                </span>
                                            )}
                                        </div>
                                    </Link>
                                </DropdownMenuItem>
                            ))}

                            {/* Theme Toggle with Switch */}
                            <div className="flex items-center p-3 rounded-xl border border-transparent">
                                <div className="flex items-center gap-2 flex-1">
                                    {mounted && isDarkMode ? (
                                        <Moon className="w-4 h-4 text-zinc-900 dark:text-zinc-100" />
                                    ) : (
                                        <Sun className="w-4 h-4 text-zinc-900 dark:text-zinc-100" />
                                    )}
                                    <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 tracking-tight leading-tight whitespace-nowrap">
                                        Dark Mode
                                    </span>
                                </div>
                                {/* Only render Switch after mount to avoid hydration mismatch */}
                                {mounted ? (
                                    <Switch 
                                        checked={isDarkMode} 
                                        onCheckedChange={toggleTheme}
                                        aria-label="Toggle dark mode"
                                    />
                                ) : (
                                    <div className="w-11 h-6" aria-hidden="true" />
                                )}
                            </div>
                        </div>

                        <DropdownMenuSeparator className="my-3 bg-linear-to-r from-transparent via-zinc-200 to-transparent dark:via-zinc-800" />

                        <DropdownMenuItem asChild>
                            <button
                                type="button"
                                onClick={() => signOut()}
                                className="w-full flex items-center gap-3 p-3 duration-200 bg-red-500/10 rounded-xl hover:bg-red-500/20 cursor-pointer border border-transparent hover:border-red-500/30 hover:shadow-sm transition-all group"
                            >
                                <LogOut className="w-4 h-4 text-red-500 group-hover:text-red-600" />
                                <span className="text-sm font-medium text-red-500 group-hover:text-red-600">
                                    Sign Out
                                </span>
                            </button>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </div>
            </DropdownMenu>
        </div>
    );
}
