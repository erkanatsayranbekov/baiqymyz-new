"use client";

import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
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
  const [loading, setLoading] = useState(false);

  const nextUrl = searchParams.get("next") || "/manager/otp";

  /**
   * @param {ApiError} error
   */
  const showManagerAuthError = (error) => {
    const status = error?.response?.status;
    if (status === 400 || status === 401) {
      toast.error(t("manager.login_invalid_credentials"));
      return;
    }
    if (status === 429) {
      toast.error(t("manager.rate_limited"));
      return;
    }
    if (status === 503) {
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

  const handleLogin = async () => {
    if (!phone || !password) {
      toast.error(t("manager.login_required"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.loginManager(phone, password);
      const token = response.data?.token;
      const username = response.data?.user?.username;
      const expiresAt = response.data?.expires_at;

      if (token) localStorage.setItem("authToken", token);
      if (username) localStorage.setItem("phone", username);
      if (expiresAt) localStorage.setItem("managerSessionExpiresAt", expiresAt);
      localStorage.setItem("authState", "authenticated");
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
            {t("manager.login_step_password")}
          </p>

          <PhoneInput
            placeholder={t("auth.phone_placeholder")}
            type="tel"
            name="manager-login-phone"
            id="manager-login-phone"
            disabled={loading}
            value={phone}
            maskOptions={PHONE_MASK_OPTIONS}
            onAccept={handlePhoneAccept}
          />
          <Input
            placeholder={t("auth.password_placeholder")}
            type="password"
            name="manager-password"
            id="manager-password"
            disabled={loading}
            value={password}
            onChange={handlePasswordChange}
          />
          <Button
            type="button"
            onClick={handleLogin}
            loading={loading}
            disabled={loading}
          >
            {t("manager.login_submit")}
          </Button>
        </div>
      </Section>
    </main>
  );
}
