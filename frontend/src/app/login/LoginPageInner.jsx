"use client";

import Image from "next/image";
import React, { useEffect, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import { useRouter } from "next/navigation";
import AuthService from "~/app/services/auth";
import PhoneInput from "~/components/PhoneInput";
import Button from "~/components/Button";
import Input from "~/components/Input";
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
  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resendAfter, setResendAfter] = useState(0);
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

  useEffect(() => {
    if (!resendAfter) return;
    const timer = window.setInterval(() => {
      setResendAfter((current) => Math.max(0, current - 1));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [resendAfter]);

  /**
   * @param {any} error
   */
  const showOtpError = (error) => {
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
      const retryAfter = Number(error?.response?.data?.retry_after || 0);
      if (retryAfter > 0) {
        setResendAfter(retryAfter);
        toast.error(t("auth.otp_too_many_requests_with_retry", { seconds: retryAfter }));
        return;
      }
      toast.error(t("auth.otp_too_many_requests"));
      return;
    }
    if (status === 400) {
      toast.error(t("auth.otp_invalid_code"));
      return;
    }
    if (status === 503) {
      toast.error(t("auth.otp_send_error"));
      return;
    }
    toast.error(t("auth.error_login"));
  };

  const handleRequestOtp = async () => {
    if (!phone) {
      toast.error(t("auth.phone_placeholder"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.requestOtp(phone);
      const retryAfter = Number(response.data?.resend_after || 0);
      setResendAfter(retryAfter);
      setOtpRequested(true);
      toast.success(response.data?.reused ? t("auth.otp_already_sent") : t("auth.otp_sent"));
    } catch (error) {
      showOtpError(error);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!otpCode) {
      toast.error(t("auth.otp_code_placeholder"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.verifyOtp(phone, otpCode);
      const phoneNumber = response.data?.user?.phone_number;
      localStorage.removeItem("authToken");
      if (phoneNumber) localStorage.setItem("phone", phoneNumber);
      localStorage.setItem("authState", "authenticated");
      AuthService.notifyAuthChanged();
      toast.success(t("auth.login_success"));
      router.push(nextUrl);
    } catch (error) {
      showOtpError(error);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * @param {React.ChangeEvent<HTMLInputElement>} event
   */
  const handleOtpCodeChange = (event) => {
    setOtpCode(event.currentTarget.value.replace(/\D/g, ""));
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
              disabled={loading || otpRequested}
              value={phone}
              maskOptions={PHONE_MASK_OPTIONS}
              // @ts-ignore
              onAccept={(val) => setPhone(val)}
              pattern="\+7-\(\d{3}\)-\d{3}-\d{2}-\d{2}"
            />

            {otpRequested && (
              <Input
                placeholder={t("auth.otp_code_placeholder")}
                type="tel"
                inputMode="numeric"
                name="otp"
                id="otp"
                maxLength={6}
                disabled={loading}
                value={otpCode}
                onChange={handleOtpCodeChange}
              />
            )}

            <Button
              type="button"
              onClick={otpRequested ? handleVerifyOtp : handleRequestOtp}
              loading={loading}
              disabled={loading}
            >
              {otpRequested ? t("auth.otp_verify") : t("auth.otp_get_code")}
            </Button>

            {otpRequested && (
              <button
                type="button"
                disabled={loading || resendAfter > 0}
                className="text-sm font-bold text-white underline disabled:text-white/50 disabled:no-underline"
                onClick={handleRequestOtp}
              >
                {resendAfter > 0
                  ? t("auth.otp_resend_after", { seconds: resendAfter })
                  : t("auth.otp_resend")}
              </button>
            )}

            <div className="mt-4 border-t border-white/30 pt-4 text-center">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-white/70">
                {t("auth.staff_access")}
              </p>
              <button
                type="button"
                className="text-sm font-bold text-white underline"
                onClick={() => router.push("/manager/login")}
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
