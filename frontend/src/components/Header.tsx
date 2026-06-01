"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import AuthService from "~/app/services/auth";
import LanguageSwitcher from "~/components/LangSwitcher";

function Header() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const syncAuth = () => {
      setIsAuthenticated(Boolean(localStorage.getItem("authToken")));
    };

    syncAuth();
    window.addEventListener("storage", syncAuth);
    window.addEventListener("auth-changed", syncAuth);

    return () => {
      window.removeEventListener("storage", syncAuth);
      window.removeEventListener("auth-changed", syncAuth);
    };
  }, []);

  const handleLogout = () => {
    AuthService.logoutLocal();
    setOpen(false);
    router.push("/");
  };

  return (
    <header className="bg-orange h-48 md:h-96 relative overflow-hidden">
      <Link href="/" aria-label="Baiqymyz">
        <Image
          className="absolute -left-10 -top-4 lg:-left-12 lg:top-10 w-64 md:w-96 m-0"
          height={500}
          width={500}
          alt="Baiqymyz"
          src={"/logo.png"}
        />
      </Link>
      <Image
        className="absolute -right-20 w-72 md:w-[500px] h-72 md:h-[500px] -bottom-32 md:-bottom-48"
        height={500}
        width={500}
        alt="image"
        src={"/oyu.png"}
      />
      <Image
        className="absolute w-full bottom-0"
        height={100}
        width={500}
        alt="image"
        src={"/white_buildings.png"}
      />
      <button
        className="absolute z-30 top-6 right-6 flex flex-col gap-1 w-10 h-10 justify-center items-center bg-white rounded shadow-md md:hidden"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={open ? "Close sidebar" : "Open sidebar"}
      >
        {open ? (
          <span className="block w-6 h-6 relative">
            <span className="absolute left-0 top-1/2 w-6 h-0.5 bg-orange rotate-45"></span>
            <span className="absolute left-0 top-1/2 w-6 h-0.5 bg-orange -rotate-45"></span>
          </span>
        ) : (
          <>
            <span className="block w-6 h-0.5 bg-orange"></span>
            <span className="block w-6 h-0.5 bg-orange"></span>
            <span className="block w-6 h-0.5 bg-orange"></span>
          </>
        )}
      </button>
      <div
        className={`fixed inset-0 bg-transparent bg-opacity-30 z-10 transition-opacity duration-300 ${
          open ? "block" : "hidden"
        }`}
        onClick={() => setOpen(false)}
      />
      <nav
        className={`fixed top-0 right-0 h-full w-64 bg-white shadow-lg z-20 transform transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        } md:static md:translate-x-0  md:bg-transparent md:shadow-none md:w-auto md:h-auto md:flex md:justify-end md:items-center md:pt-4 md:pr-4 md:gap-4`}
      >
        <ul className="flex flex-col text-center gap-6 p-8 md:flex-row md:gap-8 md:p-0 md:bg-[rgba(255,255,255,0.15)] md:max-w-[80%] md:py-2 md:px-4 md:rounded-xl">
          <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
            <Link href="/">{t("nav.home")}</Link>
          </li>
          <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
            <Link href="/#program">{t("nav.program")}</Link>
          </li>
          <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
            {isAuthenticated ? (
              <button type="button" onClick={handleLogout} className="cursor-pointer">
                {t("nav.logout")}
              </button>
            ) : (
              <Link href="/login">{t("nav.login_sms")}</Link>
            )}
          </li>
          <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
            <Link href="/#contacts">{t("nav.contact")}</Link>
          </li>
        </ul>
        <div className="px-8 lg:px-0">
          <LanguageSwitcher />
        </div>
      </nav>
    </header>
  );
}

export default Header;
