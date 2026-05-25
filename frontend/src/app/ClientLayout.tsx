"use client";

import { I18nextProvider } from "react-i18next";
import i18n from "~/lib/i18n";
import { useEffect, useState } from "react";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    i18n.on("initialized", () => setReady(true));
    if (i18n.isInitialized) setReady(true);
  }, []);

  if (!ready) return null;

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
