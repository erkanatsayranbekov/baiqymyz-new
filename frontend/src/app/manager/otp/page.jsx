"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ToastContainer, toast } from "react-toastify";
import AuthService from "~/app/services/auth";
import Button from "~/components/Button";
import PhoneInput from "~/components/PhoneInput";
import Section from "~/components/Section";
import { useTranslation } from "react-i18next";

const PHONE_MASK_OPTIONS = { mask: "+0 (000) 000-00-00" };

/**
 * @typedef {{ phone: string, otp: string }} ManagerOtpResult
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
  const [phone, setPhone] = useState("");
  const [result, setResult] = useState(
    /** @type {ManagerOtpResult | null} */ (null),
  );
  const [loading, setLoading] = useState(false);

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

  /**
   * @param {ApiError} error
   */
  const showError = (error) => {
    const status = error?.response?.status;
    if (status === 400) {
      toast.error(t("manager.invalid_phone"));
      return;
    }
    if (status === 401) {
      toast.error(t("manager.unauthorized"));
      AuthService.logoutManagerLocal();
      router.push("/manager/login?next=/manager/otp");
      return;
    }
    if (status === 403) {
      toast.error(t("manager.forbidden"));
      setAllowed(false);
      return;
    }
    if (status === 429) {
      toast.error(t("manager.rate_limited"));
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

  const handleGenerate = async () => {
    if (!phone) {
      toast.error(t("manager.invalid_phone"));
      return;
    }

    setLoading(true);
    try {
      const response = await AuthService.generateManagerOtp(phone);
      setResult(response.data);
      toast.success(t("manager.generated"));
    } catch (error) {
      showError(/** @type {ApiError} */ (error));
    } finally {
      setLoading(false);
    }
  };

  const copyOtp = async () => {
    if (!result?.otp) return;

    try {
      await navigator.clipboard.writeText(result.otp);
      toast.success(t("manager.copied"));
    } catch (_error) {
      toast.error(t("manager.copy_failed"));
    }
  };

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
              <p className="max-w-xl text-center text-sm font-bold text-white/90">
                {t("manager.description")}
              </p>
              <PhoneInput
                placeholder={t("auth.phone_placeholder")}
                type="tel"
                name="phone"
                id="manager-phone"
                disabled={loading}
                maskOptions={PHONE_MASK_OPTIONS}
                onAccept={handlePhoneAccept}
              />
              <Button
                type="button"
                onClick={handleGenerate}
                loading={loading}
                disabled={loading}
              >
                {t("manager.generate")}
              </Button>

              {result && (
                <div className="w-full max-w-md rounded-2xl bg-white p-5 text-orange shadow-lg">
                  <p className="text-sm font-bold text-black/60">
                    {t("manager.normalized_phone")}
                  </p>
                  <p className="mb-4 text-xl font-extrabold">{result.phone}</p>
                  <p className="text-sm font-bold text-black/60">
                    {t("manager.otp_code")}
                  </p>
                  <div className="mt-1 flex items-center justify-between gap-4">
                    <p className="tracking-[0.35em] text-4xl font-extrabold">
                      {result.otp}
                    </p>
                    <button
                      type="button"
                      className="rounded-xl bg-orange px-4 py-3 text-sm font-extrabold text-white"
                      onClick={copyOtp}
                    >
                      {t("manager.copy")}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </Section>
    </main>
  );
}
