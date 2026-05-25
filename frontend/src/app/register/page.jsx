"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Loading from "~/components/Loading";

export default function RegisterCompatibilityPage() {
  const router = useRouter();

  useEffect(() => {
    const query = window.location.search.replace(/^\?/, "");
    router.replace(query ? `/login?${query}` : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[url(/background.png)] bg-contain">
      <Loading color="orange" />
    </main>
  );
}
