"use client";

import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ToastContainer, toast } from "react-toastify";
import AuthService from "~/app/services/auth";
import Button from "~/components/Button";
import Input from "~/components/Input";
import PhoneInput from "~/components/PhoneInput";
import Section from "~/components/Section";

const PHONE_MASK_OPTIONS = { mask: "+0 (000) 000-00-00" };

/**
 * @typedef {{ response?: { status?: number, data?: { detail?: string, retry_after?: number } } }} ApiError
 */

export default function ManagerLoginInner() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const searchParams = useSearchParams();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [ticket, setTicket] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resendAfter, setResendAfter] = useState(0);
  const requestOtpInFlight = useRef(false);

  const nextUrl = searchParams.get("next") || "/manager/otp";

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
   * @param {ApiError} error
   */
  const showManagerAuthError = (error) => {
    const status = error?.response?.status;
    if (status === 400 || status === 401) {
      toast.error(otpSent ? t("manager.login_invalid_code") : t("manager.login_invalid_credentials"));
      return;
    }
    if (status === 429) {
      const retryAfter = normalizeDelay(error?.response?.data?.retry_after);
      if (retryAfter > 0) {
        setResendAfter(retryAfter);
        toast.error(t("auth.otp_too_many_requests_with_retry", { seconds: retryAfter }));
        return;
      }
      toast.error(t("manager.rate_limited"));
      return;
    }
    if (status === 503) {
      if (error?.response?.data?.detail === "OTP could not be sent.") {
        toast.error(t("auth.otp_send_error"));
        return;
      }
      toast.error(t("manager.login_disabled"));
      return;
    }
    toast.error(t("manager.server_error"));
  };

  /**
   * @param {string} value
   */
  const handlePhoneAccept = (value) => {
    setPhone(value);
  };

  /**
   * @param {import("react").ChangeEvent<HTMLInputElement>} event
   */
  const handlePasswordChange = (event) => {
    setPassword(event.currentTarget.value);
  };

  /**
   * @param {import("react").ChangeEvent<HTMLInputElement>} event
   */
  const handleCodeChange = (event) => {
    setCode(event.currentTarget.value.replace(/\D/g, ""));
  };

  const handleRequestOtp = async () => {
    if (requestOtpInFlight.current) return;

    if (!phone || !password) {
      toast.error(t("manager.login_required"));
      return;
    }

    requestOtpInFlight.current = true;
    setLoading(true);
    try {
      const response = await AuthService.requestManagerOtp(phone, password);
      setTicket(response.data?.ticket || "");
      setOtpSent(true);
      setResendAfter(normalizeDelay(response.data?.resend_after));
      setPassword("");
      toast[response.data?.reused ? "info" : "success"](
        response.data?.reused ? t("auth.otp_already_sent") : t("auth.otp_sent"),
      );
    } catch (error) {
      showManagerAuthError(/** @type {ApiError} */ (error));
    } finally {
      requestOtpInFlight.current = false;
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!phone || !ticket || !code) {
      toast.error(t("auth.otp_code_placeholder"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.verifyManagerOtp(phone, ticket, code);
      const token = response.data?.token;
      const username = response.data?.user?.username;
      const expiresAt = response.data?.expires_at;

      if (token) localStorage.setItem("authToken", token);
      if (username) localStorage.setItem("phone", username);
      if (expiresAt) localStorage.setItem("managerSessionExpiresAt", expiresAt);
      AuthService.notifyAuthChanged();

      toast.success(t("manager.login_success"));
      router.push(nextUrl);
    } catch (error) {
      showManagerAuthError(/** @type {ApiError} */ (error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[url(/background.png)] bg-contain">
      <ToastContainer />
      <Section>
        <div className="rounded-4xl relative m-4 flex min-w-[80%] flex-col items-center justify-center gap-4 bg-[#dd6c38] px-6 py-12 text-white">
          <Button
            className="absolute top-6 left-6 h-10! w-fit! px-4!"
            onClick={() => router.push("/login")}
            aria-label={t("common.back")}
          >
            <img src="/back.svg" alt="" className="w-6" />
          </Button>
          <Image height={100} width={100} alt="image" src={"/logo_white.png"} />
          <h1 className="mb-2 text-center font-extrabold text-2xl text-white">
            {t("manager.login_title")}
          </h1>
          <p className="rounded-full bg-white/15 px-4 py-1 text-xs font-extrabold uppercase tracking-[0.16em] text-white/80">
            {t("manager.staff_only")}
          </p>
          <p className="max-w-xl text-center font-bold text-sm text-white/90">
            {otpSent ? t("manager.login_step_otp") : t("manager.login_step_password")}
          </p>

          <PhoneInput
            placeholder={t("auth.phone_placeholder")}
            type="tel"
            name="manager-login-phone"
            id="manager-login-phone"
            disabled={loading || otpSent}
            value={phone}
            maskOptions={PHONE_MASK_OPTIONS}
            onAccept={handlePhoneAccept}
          />
          {!otpSent && (
            <Input
              placeholder={t("auth.password_placeholder")}
              type="password"
              name="manager-password"
              id="manager-password"
              disabled={loading}
              value={password}
              onChange={handlePasswordChange}
            />
          )}
          {otpSent && (
            <Input
              placeholder={t("auth.otp_code_placeholder")}
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={8}
              disabled={loading}
              name="manager-otp-code"
              id="manager-otp-code"
              value={code}
              onChange={handleCodeChange}
            />
          )}
          <Button
            type="button"
            onClick={otpSent ? handleVerify : handleRequestOtp}
            loading={loading}
            disabled={loading || (!otpSent && resendAfter > 0)}
          >
            {!otpSent && resendAfter > 0
              ? t("auth.otp_resend_after", { seconds: resendAfter })
              : otpSent
                ? t("manager.login_submit")
                : t("manager.login_get_code")}
          </Button>
          {otpSent && resendAfter > 0 && (
            <p className="text-center text-sm font-bold text-white/80">
              {t("auth.otp_resend_after", { seconds: resendAfter })}
            </p>
          )}
          {otpSent && (
            <button
              type="button"
              className="font-bold text-white underline disabled:opacity-60"
              disabled={loading}
              onClick={() => {
                setOtpSent(false);
                setCode("");
                setTicket("");
                setResendAfter(0);
              }}
            >
              {t("manager.login_change_phone")}
            </button>
          )}
        </div>
      </Section>
    </main>
  );
}
