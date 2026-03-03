"use client";

import dynamic from "next/dynamic";

const ProfileDropdown = dynamic(() => import("@/components/profile-dropdown"), {
    ssr: false,
});

export default ProfileDropdown;
