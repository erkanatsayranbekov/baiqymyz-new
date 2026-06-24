"use client";

import Image from "next/image";
import React, { useEffect, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import { useRouter } from "next/navigation";
import AuthService from "~/app/services/auth";
import PhoneInput from "~/components/PhoneInput";
import Button from "~/components/Button";
import Section from "~/components/Section";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";

const PHONE_MASK_OPTIONS = {
  mask: "+0 (000) 000-00-00",
};

export default function LoginPage() {
  const { t } = useTranslation("common");

  const searchParams = useSearchParams();
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [deviceConflict, setDeviceConflict] = useState(
    /** @type {{ boundPhoneMask: string } | null} */ (null)
  );
  const router = useRouter();
  const rawNext = searchParams.get("next");
  const nextUrl = rawNext?.startsWith("/") && !rawNext.startsWith("//")
    ? rawNext
    : "/";

  useEffect(() => {
    const registered = searchParams.get("registered");
    const passwordChanged = searchParams.get("success");
    if (registered) toast.success(t("auth.registration_success"));

    if (passwordChanged) toast.success(t("auth.password_changed_success"));
  }, []);

  /**
   * @param {any} error
   */
  const showLoginError = (error) => {
    const status = error?.response?.status;
    if (
      status === 409 &&
      error?.response?.data?.code === "DEVICE_BOUND_TO_OTHER_PHONE"
    ) {
      AuthService.logoutLocal();
      setDeviceConflict({
        boundPhoneMask: error.response.data?.bound_phone_mask || "",
      });
      return;
    }
    if (status === 429) {
      toast.error(t("auth.too_many_requests"));
      return;
    }
    toast.error(t("auth.error_login"));
  };

  const handleLogin = async () => {
    if (!phone) {
      toast.error(t("auth.phone_placeholder"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.loginByPhone(phone);
      const phoneNumber = response.data?.user?.phone_number;
      if (phoneNumber) localStorage.setItem("phone", phoneNumber);
      localStorage.setItem("authState", "authenticated");
      AuthService.notifyAuthChanged();
      toast.success(t("auth.login_success"));
      router.push(nextUrl);
    } catch (error) {
      showLoginError(error);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <main className="bg-contain">
        <ToastContainer />
        <Section>
          <div className="rounded-4xl flex flex-col py-12 gap-4 min-w-[80%] m-4 items-center justify-center bg-[#dd6c38] text-white px-6">
            <Image
              className="w-24"
              height={150}
              width={150}
              alt="image"
              src={"/logo_white.png"}
            />
            <h1 className="text-2xl font-extrabold text-white mb-2">
              {t("auth.login_title")}
            </h1>
            <p className="max-w-md text-center text-sm font-bold text-white/90">
              {t("auth.login_help")}
            </p>

            <PhoneInput
              placeholder={t("auth.phone_placeholder")}
              type="tel"
              name="phone"
              id="phone"
              disabled={loading}
              value={phone}
              maskOptions={PHONE_MASK_OPTIONS}
              // @ts-ignore
              onAccept={(val) => setPhone(val)}
              pattern="\+7-\(\d{3}\)-\d{3}-\d{2}-\d{2}"
            />
            <Button
              type="button"
              onClick={handleLogin}
              loading={loading}
              disabled={loading}
            >
              {t("auth.phone_login_submit")}
            </Button>
            <div className="mt-4 border-t border-white/30 pt-4 text-center">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-white/70">
                {t("auth.staff_access")}
              </p>
              <button
                type="button"
                className="text-sm font-bold text-white underline"
                onClick={() => router.push("/manager/login?next=/manager/otp")}
              >
                {t("auth.manager_login")}
              </button>
            </div>
          </div>
        </Section>
      </main>
      {deviceConflict && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 px-4">
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 text-center shadow-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="login-device-conflict-title"
          >
            <h2
              id="login-device-conflict-title"
              className="mb-4 text-2xl font-extrabold text-orange"
            >
              {t("home.device_conflict_title")}
            </h2>
            <p className="mb-6 text-sm font-bold text-gray-700">
              {t("home.device_conflict_text", {
                phone:
                  deviceConflict.boundPhoneMask ||
                  t("home.device_conflict_unknown_phone"),
              })}
            </p>
            <button
              type="button"
              onClick={() => setDeviceConflict(null)}
              className="min-h-14 w-full rounded-2xl bg-orange px-5 py-3 text-center text-sm font-extrabold leading-tight text-white"
            >
              {t("home.device_conflict_button")}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
