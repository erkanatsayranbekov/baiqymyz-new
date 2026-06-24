"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import AuthService from "~/app/services/auth";
import Button from "~/components/Button";
import Section from "~/components/Section";
import { useTranslation } from "react-i18next";

/**
 * @typedef {{ username?: string, is_staff?: boolean, is_superuser?: boolean, manager_session_expires_at?: string }} ManagerUser
 * @typedef {{ response?: { status?: number } }} ApiError
 */

export default function ManagerOtpPage() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [allowed, setAllowed] = useState(false);
  const [managerUser, setManagerUser] = useState(
    /** @type {ManagerUser | null} */ (null),
  );

  useEffect(() => {
    const loginUrl = "/manager/login?next=/manager/otp";
    const token = localStorage.getItem("authToken");
    if (!token) {
      router.push(loginUrl);
      return;
    }

    AuthService.getManagerMe()
      .then((response) => {
        const user = response.data;
        setManagerUser(user);
        setAllowed(Boolean(user?.is_staff || user?.is_superuser));
      })
      .catch((error) => {
        if (error?.response?.status === 401) {
          AuthService.logoutManagerLocal();
          router.push(loginUrl);
          return;
        }
        if (error?.response?.status === 403) {
          setAllowed(false);
          return;
        }
        toast.error(t("manager.access_error"));
      })
      .finally(() => setCheckingAccess(false));
  }, [router, t]);

  const logoutManager = () => {
    AuthService.logoutManagerLocal();
    router.push("/manager/login?next=/manager/otp");
  };

  return (
    <main className="bg-[url(/background.png)] bg-contain min-h-screen">
      <ToastContainer />
      <Section>
        <div className="rounded-4xl relative flex flex-col py-12 gap-4 min-w-[80%] m-4 items-center justify-center bg-[#dd6c38] text-white px-6">
          <Button
            className="absolute top-6 left-6 w-fit! h-10! px-4!"
            onClick={() => router.back()}
            aria-label={t("common.back")}
          >
            <img src="/back.svg" alt="" className="w-6" />
          </Button>
          <Image
            height={100}
            width={100}
            alt="image"
            src={"/logo_white.png"}
          />
          <h1 className="text-2xl font-extrabold text-white mb-2">
            {t("manager.title")}
          </h1>

          {checkingAccess ? (
            <p className="text-lg font-bold">{t("manager.checking_access")}</p>
          ) : !allowed ? (
            <>
              <p className="text-lg font-bold text-center">
                {t("manager.access_denied")}
              </p>
              <Button type="button" onClick={logoutManager}>
                {t("manager.login_as_manager")}
              </Button>
            </>
          ) : (
            <>
              <div className="flex w-full max-w-xl flex-col items-center justify-between gap-3 rounded-2xl bg-white/15 p-4 text-center md:flex-row md:text-left">
                <div>
                  <p className="font-bold text-xs uppercase tracking-[0.14em] text-white/70">
                    {t("manager.signed_in_as")}
                  </p>
                  <p className="font-extrabold text-lg">
                    {managerUser?.username || t("manager.manager")}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-xl bg-white px-4 py-2 font-extrabold text-orange text-sm"
                  onClick={logoutManager}
                >
                  {t("manager.logout")}
                </button>
              </div>
              <div className="w-full max-w-xl rounded-2xl bg-white p-5 text-center text-orange shadow-lg">
                <p className="text-lg font-extrabold">
                  {t("manager.otp_removed_title")}
                </p>
                <p className="mt-2 text-sm font-bold text-black/60">
                  {t("manager.otp_removed_text")}
                </p>
              </div>
            </>
          )}
        </div>
      </Section>
    </main>
  );
}
