"use client";

import { Suspense } from "react";
import ManagerLoginInner from "./ManagerLoginInner";

export default function ManagerLoginPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ManagerLoginInner />
    </Suspense>
  );
}
