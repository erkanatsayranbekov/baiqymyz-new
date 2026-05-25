"use client";

import Image from "next/image";
import React from "react";
import { useRouter } from "next/navigation";
import { ToastContainer } from "react-toastify";
import Button from "~/components/Button";
import Section from "~/components/Section";
import { useTranslation } from "react-i18next";

export default function SignUpPage() {
  const { t } = useTranslation("common");
  const router = useRouter();

  return (
    <>
      <main className="bg-[url(/background.png)] bg-contain">
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
              {t("auth.forgot_password_title")}
            </h1>
            <p className="max-w-[360px] text-center text-lg text-white">
              {t("auth.passwordless_login_hint")}
            </p>
            <Button type="button" onClick={() => router.push("/login")}>
              {t("auth.go_to_login")}
            </Button>
          </div>
        </Section>
      </main>
    </>
  );
}
