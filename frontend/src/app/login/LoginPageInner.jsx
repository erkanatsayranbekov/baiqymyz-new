"use client";

import Image from "next/image";
import React, { useEffect, useRef, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import { useRouter } from "next/navigation";
import AuthService from "~/app/services/auth";
import Input from "~/components/Input";
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
  const [code, setCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resendAfter, setResendAfter] = useState(0);
  const requestOtpInFlight = useRef(false);
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
    if (resendAfter <= 0) return;

    const timer = window.setTimeout(() => {
      setResendAfter((current) => Math.max(current - 1, 0));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [resendAfter]);

  /**
   * @param {unknown} value
   */
  const normalizeDelay = (value) => {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? Math.max(Math.ceil(numberValue), 0) : 0;
  };

  /**
   * @param {any} data
   */
  const applyOtpRequestState = (data) => {
    const nextResendAfter = normalizeDelay(data?.resend_after ?? data?.retry_after);
    setOtpSent(true);
    setResendAfter(nextResendAfter);

    if (data?.reused) {
      toast.info(t("auth.otp_already_sent"));
      return;
    }

    if (data?.manual_fallback_required) {
      toast.info(t("auth.otp_manual_fallback_required"));
      return;
    }

    toast.success(t("auth.otp_sent"));
  };

  /**
   * @param {any} error
   */
  const showOtpError = (error) => {
    const status = error?.response?.status;
    if (status === 429) {
      const retryAfter = normalizeDelay(error?.response?.data?.retry_after);
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
    toast.error(t("auth.error_login"));
  };

  const handleRequestOtp = async () => {
    if (requestOtpInFlight.current) return;

    if (!phone) {
      toast.error(t("auth.phone_placeholder"));
      return;
    }

    requestOtpInFlight.current = true;
    setLoading(true);
    try {
      const response = await AuthService.requestOtp(phone);
      applyOtpRequestState(response.data);
    } catch (error) {
      showOtpError(error);
      console.error(error);
    } finally {
      requestOtpInFlight.current = false;
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!phone || !code) {
      toast.error(t("auth.otp_code_placeholder"));
      return;
    }

    setLoading(true);
    try {
      const res = await AuthService.verifyOtp(phone, code);
      if (res.status === 201 || res.status === 200) {
        const phoneNumber = res.data?.user?.phone_number;
        const token = res.data?.token;

        if (phoneNumber) localStorage.setItem("phone", phoneNumber);
        if (token) localStorage.setItem("authToken", token);
        AuthService.notifyAuthChanged();

        try {
          const me = await AuthService.getMe();
          if (me.data?.is_staff || me.data?.is_superuser) {
            toast.info(t("auth.manager_secure_login_hint"));
            router.push("/manager/login?next=/manager/otp");
            return;
          }
        } catch (_error) {
          // The regular login still succeeds even if the role hint check fails.
        }

        router.push(nextUrl);
      }
    } catch (err) {
      showOtpError(err);
      console.error(err);
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
              disabled={loading || otpSent}
              value={phone}
              maskOptions={PHONE_MASK_OPTIONS}
              // @ts-ignore
              onAccept={(val) => setPhone(val)}
              pattern="\+7-\(\d{3}\)-\d{3}-\d{2}-\d{2}"
            />
            {otpSent && (
              <Input
                placeholder={t("auth.otp_code_placeholder")}
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={8}
                disabled={loading}
                name="otp-code"
                id="otp-code"
                value={code}
                // @ts-ignore
                onChange={(e) => setCode(e.currentTarget.value.replace(/\D/g, ""))}
              />
            )}
            <Button
              type="button"
              onClick={otpSent ? handleVerifyOtp : handleRequestOtp}
              loading={loading}
              disabled={loading || (!otpSent && resendAfter > 0)}
            >
              {!otpSent && resendAfter > 0
                ? t("auth.otp_resend_after", { seconds: resendAfter })
                : otpSent
                  ? t("auth.otp_verify")
                  : t("auth.otp_get_code")}
            </Button>
            {otpSent && (
              <button
                type="button"
                className="text-lg text-white underline disabled:opacity-60"
                disabled={loading || resendAfter > 0}
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
                onClick={() => router.push("/manager/login?next=/manager/otp")}
              >
                {t("auth.manager_login")}
              </button>
            </div>
          </div>
        </Section>
      </main>
    </>
  );
}
