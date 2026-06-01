"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Map, Placemark, YMaps } from "@pbe/react-yandex-maps";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import AuthService from "~/app/services/auth";
import LanguageSwitcher from "~/components/LangSwitcher";

const cultureCards = [
  { image: "/landing/0831.png", key: "kumys" },
  { image: "/landing/0832.png", key: "horse" },
  { image: "/landing/0833.png", key: "showoff" },
  { image: "/landing/0834.png", key: "participants" },
  { image: "/landing/0835.png", key: "food" },
];

const sportCards = [
  { image: "/landing/0821.png", label: "АСАУ ҮЙРЕТУ" },
  { image: "/landing/0822.png", label: "ШАЛУ" },
  { image: "/landing/0823.png", label: "АУДАРЫСПАҚ" },
  { image: "/landing/0824.png", label: "ҚҰМАЙ ТАЗЫ САЙЫСЫ" },
  { image: "/landing/0825.png", label: "ҚОШҚАР КӨТЕРУ" },
  { image: "/landing/0826.png", label: "МЕШКЕЙЛЕР ЖАРЫСЫ" },
];

const scienceCards = [
  {
    image: "/landing/0837.png",
    title: "science_1_title",
    name: "science_1_name",
    description: "science_1_description",
  },
  {
    image: "/landing/0839.jpg",
    title: "science_2_title",
    name: "science_2_name",
    description: "science_2_description",
  },
  {
    image: "/landing/0840.jpg",
    title: "science_3_title",
    name: "science_3_name",
    description: "science_3_description",
  },
  {
    image: "/landing/0837.png",
    title: "science_4_title",
    name: "science_4_name",
    description: "science_4_description",
  },
];

const youtubeCards = [
  "/landing/0845.png",
  "/landing/0846.jpg",
  "/landing/0847.png",
];

const EVENT_COORDINATES: [number, number] = [49.4129, 75.4743];

export default function HomePage() {
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

  const closeMenu = () => setOpen(false);

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f3cf77] bg-[url('/landing/0801_original.png')] bg-repeat">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col overflow-hidden bg-[#f6d684] shadow-2xl shadow-amber-950/20">
        <section className="relative min-h-[700px] overflow-hidden bg-[url('/landing/0801.png')] bg-cover bg-center px-5 py-5 sm:px-8 lg:px-14">
          <div className="absolute inset-0 bg-gradient-to-r from-black/55 via-black/25 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 h-36 bg-gradient-to-t from-black/30 to-transparent" />

          <div className="relative z-20 flex items-start justify-between gap-6">
            <Link href="/" aria-label="Baiqymyz" onClick={closeMenu}>
              <Image
                src="/landing/logo.png"
                alt="Baiqymyz"
                width={220}
                height={160}
                priority
                className="h-auto w-28 sm:w-36 lg:w-44"
              />
            </Link>

            <button
              type="button"
              className="z-30 flex h-11 w-11 items-center justify-center rounded-xl bg-white shadow-md md:hidden"
              onClick={() => setOpen((current) => !current)}
              aria-label={open ? "Close navigation" : "Open navigation"}
            >
              {open ? (
                <span className="relative block h-6 w-6">
                  <span className="absolute left-0 top-1/2 h-0.5 w-6 rotate-45 bg-orange" />
                  <span className="absolute left-0 top-1/2 h-0.5 w-6 -rotate-45 bg-orange" />
                </span>
              ) : (
                <span className="flex flex-col gap-1.5">
                  <span className="block h-0.5 w-6 bg-orange" />
                  <span className="block h-0.5 w-6 bg-orange" />
                  <span className="block h-0.5 w-6 bg-orange" />
                </span>
              )}
            </button>

            <div
              className={`fixed inset-0 z-10 bg-black/20 transition-opacity md:hidden ${
                open ? "block" : "hidden"
              }`}
              onClick={closeMenu}
            />

            <nav
              className={`fixed right-0 top-0 z-20 h-full w-72 transform bg-white shadow-2xl transition-transform duration-300 md:static md:h-auto md:w-auto md:translate-x-0 md:bg-transparent md:shadow-none ${
                open ? "translate-x-0" : "translate-x-full"
              }`}
            >
              <div className="flex h-full flex-col gap-6 p-8 md:h-auto md:flex-row md:items-center md:p-0">
                <div className="flex flex-col gap-4 rounded-2xl md:flex-row md:items-center md:bg-white/15 md:p-2 md:backdrop-blur-sm">
                  <Link
                    href="/"
                    onClick={closeMenu}
                    className="rounded-lg px-3 py-2 text-sm font-extrabold text-orange transition hover:bg-orange/10 md:bg-white/30 md:text-white md:hover:bg-white/20"
                  >
                    {t("nav.home")}
                  </Link>
                  <Link
                    href="/#program"
                    onClick={closeMenu}
                    className="rounded-lg px-3 py-2 text-sm font-extrabold text-orange transition hover:bg-orange/10 md:bg-white/30 md:text-white md:hover:bg-white/20"
                  >
                    {t("nav.program")}
                  </Link>
                  {isAuthenticated ? (
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="rounded-lg px-3 py-2 text-left text-sm font-extrabold text-orange transition hover:bg-orange/10 md:bg-white/30 md:text-white md:hover:bg-white/20"
                    >
                      {t("nav.logout")}
                    </button>
                  ) : (
                    <Link
                      href="/login"
                      onClick={closeMenu}
                      className="rounded-lg px-3 py-2 text-sm font-extrabold text-orange transition hover:bg-orange/10 md:bg-white/30 md:text-white md:hover:bg-white/20"
                    >
                      {t("nav.login_sms")}
                    </Link>
                  )}
                  <Link
                    href="/#contacts"
                    onClick={closeMenu}
                    className="rounded-lg px-3 py-2 text-sm font-extrabold text-orange transition hover:bg-orange/10 md:bg-white/30 md:text-white md:hover:bg-white/20"
                  >
                    {t("nav.contact")}
                  </Link>
                </div>
                <LanguageSwitcher />
              </div>
            </nav>
          </div>

          <div className="relative z-10 mt-20 flex max-w-2xl flex-col items-start gap-8 lg:mt-24">
            <p className="rounded-full bg-white/20 px-5 py-2 text-sm font-extrabold uppercase tracking-[0.18em] text-white backdrop-blur-sm">
              {t("landing.event_kicker")}
            </p>
            <h1 className="text-4xl font-black uppercase leading-tight text-white drop-shadow-[0_4px_16px_rgba(0,0,0,0.85)] sm:text-5xl lg:text-6xl">
              {t("landing.title")}
            </h1>
            <button
              type="button"
              onClick={() => router.push("/vote")}
              className="min-h-14 w-full max-w-xs rounded-2xl bg-white px-8 py-4 text-center text-lg font-black uppercase text-orange shadow-xl shadow-black/30 transition hover:-translate-y-0.5 hover:shadow-2xl"
            >
              {t("landing.button")}
            </button>
          </div>
        </section>

        <section className="bg-white px-5 py-10 sm:px-8 lg:px-14">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div className="rounded-3xl bg-[url('/landing/0806.png')] bg-cover bg-center p-8 text-center text-white shadow-xl">
              <p className="text-3xl font-black uppercase sm:text-4xl">
                «BAI QYMYZ»
              </p>
              <p className="mt-2 text-4xl font-black uppercase sm:text-5xl">
                {t("landing.date")}
              </p>
              <p className="mt-3 text-xl font-black uppercase">
                {t("landing.location")}
              </p>
            </div>
            <div className="text-lg font-extrabold uppercase leading-relaxed text-[#b36b09]">
              <p>{t("landing.description")}</p>
              <p className="mt-5">{t("landing.description2")}</p>
            </div>
          </div>
        </section>

        <section className="relative h-48 bg-white sm:h-56">
          <Image
            src="/landing/0829.png"
            alt={t("landing.gallery_alt")}
            fill
            className="object-cover"
          />
        </section>

        <section id="program" className="scroll-mt-8 bg-[#f5d17e] px-5 py-14 sm:px-8 lg:px-14">
          <div className="relative overflow-hidden rounded-3xl bg-[url('/landing/0806.png')] bg-cover bg-center p-7 shadow-xl sm:p-10 lg:min-h-60">
            <Image
              src="/landing/0805.png"
              alt={t("landing.kumys_image_alt")}
              width={360}
              height={360}
              className="absolute -bottom-12 left-2 hidden w-80 lg:block"
            />
            <div className="relative z-10 ml-auto max-w-2xl text-white lg:py-8">
              <p className="text-3xl font-black uppercase sm:text-5xl">
                «BAI QYMYZ»
              </p>
              <p className="mt-2 text-2xl font-black uppercase sm:text-4xl">
                {t("landing.headline")}
              </p>
            </div>
          </div>

          <SectionTitle>{t("landing.program")}</SectionTitle>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {cultureCards.map((card) => (
              <article
                key={card.key}
                className="overflow-hidden rounded-3xl bg-[#8a4f1e] shadow-xl shadow-amber-950/15"
              >
                <div className="relative h-64 lg:h-72">
                  <Image
                    src={card.image}
                    alt={t(`landing.${card.key}`)}
                    fill
                    sizes="(min-width: 1024px) 210px, (min-width: 640px) 50vw, 100vw"
                    className="object-cover"
                  />
                </div>
                <div className="flex min-h-20 items-center bg-[url('/landing/0836.png')] bg-cover px-5 py-4">
                  <p className="text-lg font-black uppercase leading-tight text-white">
                    {t(`landing.${card.key}`)}
                  </p>
                </div>
              </article>
            ))}
          </div>

          <div className="mt-14 overflow-hidden rounded-3xl bg-[url('/landing/0813.png')] bg-cover bg-center p-8 shadow-xl lg:p-14">
            <div className="ml-auto max-w-md text-white">
              <h2 className="text-4xl font-black uppercase lg:text-5xl">
                {t("landing.ethno_title")}
              </h2>
              <p className="mt-5 text-base font-bold leading-relaxed lg:text-lg">
                {t("landing.ethno_text")}
              </p>
            </div>
          </div>
        </section>

        <section className="bg-white px-5 py-14 sm:px-8 lg:px-14">
          <SectionTitle>{t("landing.science_title")}</SectionTitle>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {scienceCards.map((card) => (
              <article
                key={card.title}
            className="flex min-h-[370px] flex-col rounded-3xl bg-[url('/landing/0838.png')] bg-cover bg-center p-5 text-white shadow-xl shadow-amber-950/15"
              >
                <p className="min-h-24 text-sm font-black uppercase leading-snug">
                  {t(`landing.${card.title}`)}
                </p>
                <Image
                  src={card.image}
                  alt={t(`landing.${card.name}`)}
                  width={120}
                  height={120}
                  className="mx-auto my-4 h-24 w-24 rounded-full object-cover ring-4 ring-white/60"
                />
                <h3 className="text-base font-black leading-tight">
                  {t(`landing.${card.name}`)}
                </h3>
                <p className="mt-3 text-xs font-semibold leading-relaxed text-white/90">
                  {t(`landing.${card.description}`)}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="bg-[#f2f4dd] px-5 py-14 sm:px-8 lg:px-14">
          <h2 className="text-center text-3xl font-black uppercase text-[#d54013] sm:text-5xl">
            {t("landing.sport")}
          </h2>
          <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {sportCards.map((card) => (
              <div key={card.image} className="flex flex-col items-center text-center">
                <Image
                  src={card.image}
                  alt={card.label}
                  width={150}
                  height={150}
                  className="h-32 w-32 object-contain"
                />
                <p className="mt-4 text-lg font-black uppercase text-[#d54013]">
                  {card.label}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white px-5 py-14 sm:px-8 lg:px-14">
          <div className="mb-8 flex flex-col gap-4 text-orange">
            <h2 className="text-3xl font-black uppercase sm:text-5xl">
              {t("landing.map_title")}
            </h2>
            <div className="flex items-center gap-3 font-black uppercase">
              <Image src="/pin.svg" alt="" width={36} height={36} className="h-9 w-9" />
              <span>{t("landing.map_location")}</span>
            </div>
          </div>
          <div className="overflow-hidden rounded-3xl border-4 border-orange shadow-xl">
            <YMaps
              query={{
                lang: "ru_RU",
                apikey: "536168cc-8dbb-4923-a06f-9a6bd5a9cf15",
              }}
            >
              <Map
                defaultState={{ center: EVENT_COORDINATES, zoom: 13 }}
                className="h-[340px] w-full"
              >
                <Placemark geometry={EVENT_COORDINATES} options={{ iconColor: "#d54013" }} />
              </Map>
            </YMaps>
          </div>
        </section>

        <section className="bg-[#f2f4dd] px-5 py-14 sm:px-8 lg:px-14">
          <SectionTitle>{t("landing.youtube_title")}</SectionTitle>
          <div className="grid gap-5 md:grid-cols-3">
            {youtubeCards.map((image) => (
              <Link
                key={image}
                href="https://www.youtube.com/@BaiQymyz"
                target="_blank"
                rel="noreferrer"
                className="group relative h-56 overflow-hidden rounded-3xl shadow-xl"
              >
                <Image
                  src={image}
                  alt={t("landing.youtube_title")}
                  fill
                  sizes="(min-width: 768px) 33vw, 100vw"
                  className="object-cover transition duration-500 group-hover:scale-105"
                />
              </Link>
            ))}
          </div>
        </section>

        <footer
          id="contacts"
          className="scroll-mt-8 rounded-t-3xl bg-[#3c9f9f] px-5 py-10 text-white sm:px-8 lg:px-14"
        >
          <div className="grid gap-8 lg:grid-cols-[160px_1fr_120px] lg:items-center">
            <Image
              src="/landing/logo_footer.png"
              alt="Baiqymyz"
              width={140}
              height={140}
              className="h-auto w-32"
            />
            <div className="flex flex-col items-start gap-5 lg:items-center">
              <div className="flex flex-wrap gap-3">
                <Link href="/" className="rounded-lg bg-white/20 px-3 py-2 text-sm font-bold">
                  {t("nav.home")}
                </Link>
                <Link
                  href="/#program"
                  className="rounded-lg bg-white/20 px-3 py-2 text-sm font-bold"
                >
                  {t("nav.program")}
                </Link>
                <Link
                  href="/#contacts"
                  className="rounded-lg bg-white/20 px-3 py-2 text-sm font-bold"
                >
                  {t("nav.contact")}
                </Link>
              </div>
              <div className="flex flex-col gap-3 text-sm font-bold md:flex-row md:items-center md:gap-8">
                <a href="mailto:info@baiqymyz.kz" className="flex items-center gap-2">
                  <Image src="/landing/mail_white.png" alt="" width={24} height={24} />
                  info@baiqymyz.kz
                </a>
                <a
                  href="https://api.whatsapp.com/send/?phone=77762010005&text=Здравствуйте%21%0A%0AХочу+узнать+про+Bai Qymyz .%0A%0A&type=phone_number&app_absent=0"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2"
                >
                  <Image src="/landing/whatsapp_white.png" alt="" width={24} height={24} />
                  WhatsApp
                </a>
                <a
                  href="https://www.instagram.com/baiqymyz.kz/"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2"
                >
                  <Image src="/landing/instagram_white.png" alt="" width={24} height={24} />
                  baiqymyz.kz
                </a>
              </div>
              <p className="font-black uppercase">Karkaraly 2026</p>
            </div>
            <Image
              src="/landing/0827.png"
              alt=""
              width={120}
              height={120}
              className="hidden h-auto w-28 lg:block"
            />
          </div>
        </footer>
      </div>
    </main>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="my-10 flex justify-center">
      <h2 className="rounded-2xl bg-[url('/landing/0815.png')] bg-cover bg-center px-8 py-4 text-center text-2xl font-black uppercase text-white shadow-lg sm:text-3xl">
        {children}
      </h2>
    </div>
  );
}
