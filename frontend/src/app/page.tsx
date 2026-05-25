"use client";

import Image from "next/image";
import { YMaps, Map, Placemark } from "@pbe/react-yandex-maps";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "~/components/LangSwitcher";
import { useRouter } from "next/navigation";
import Section from "~/components/Section";
import Footer from "~/components/Footer";
import Button from "~/components/Button";
import Header from "~/components/Header";
import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const { t } = useTranslation("common");
  const [open, setOpen] = useState(false);
  const router = useRouter();
 
  return (
    <main className="bg-[url(/background.png)] bg-contain min-h-screen flex flex-col">
      <div className="max-w-[1500px] lg:w-[1200px] mx-auto bg-white flex flex-col">
        <header className="bg-[url(/landing/0801.png)] bg-cover bg-center h-144 lg:h-[700px] relative overflow-hidden p-6 lg:p-12">
          <div className="absolute inset-0 bg-black/35" aria-hidden="true" />
          <Link href="/" aria-label="Baiqymyz">
            <Image
              className="absolute left-4 top-4 lg:left-12 lg:top-10 w-24 m-0"
              height={200}
              width={200}
              alt="Baiqymyz"
              src={"/landing/logo.png"}
            />
          </Link>
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
            <ul className="flex flex-col items-baseline lg:items-center gap-6 p-8 md:flex-row md:gap-8 md:p-0 md:bg-[rgba(255,255,255,0.15)] md:max-w-[80%] md:py-2 md:px-4 md:rounded-xl">
              <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
                <Link href="/">{t("nav.home")}</Link>
              </li>
              <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
                <Link href="/#program">{t("nav.program")}</Link>
              </li>
              <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
                <Link href="/login">{t("nav.login_sms")}</Link>
              </li>
              <li className="text-orange md:text-white md:bg-[rgba(255,255,255,0.3)] md:px-2 md:rounded-lg cursor-pointer">
                <Link href="/#contacts">{t("nav.contact")}</Link>
              </li>
            </ul>
            <div className="px-8 lg:px-0">
              <LanguageSwitcher />
            </div>
          </nav>
          <div className="relative h-full flex flex-col justify-end lg:justify-center items-baseline text-center lg:text-left lg:w-2xl">
            <div className="mb-20">
              <h1 className="text-white text-2xl lg:text-4xl font-bold drop-shadow-[0_3px_12px_rgba(0,0,0,0.85)]">
                {t("landing.title")}
              </h1>
            </div>
            <Button onClick={() => router.push("/vote")}>
              {t("landing.button")}
            </Button>
          </div>
        </header>
        <Image
          className="w-full top-0"
          height={20}
          width={500}
          alt="image"
          src="/oyu_2_small.png"
        />

        <div className="flex flex-col lg:flex-row p-6 lg:p-12 gap-16 lg:gap-32">
          <div className="p-4 text-white text-center font-bold bg-linear-to-r from-yellow-500 to-orange-400 rounded-lg shadow-lg w-full lg:w-1/2 flex-1">
            <h1 className="text-4xl">«BAI QYMYZ 2025»</h1>
            <h1 className="text-3xl">{t("landing.date")}</h1>
            <h1 className="text-xl">{t("landing.location")}</h1>
          </div>
          <div className="text-orange font-bold flex-1">
            <p className="block">{t("landing.description")}</p>
            <p className="block mt-4">{t("landing.description2")}</p>
          </div>
        </div>
        <div className="w-full h-[200px] relative">
          <Image
            className="object-cover"
            fill
            alt="image"
            src="/landing/0829.png"
          />
        </div>

        <div id="program" className="bg-yellow-500 p-12 scroll-mt-8">
          <div className="h-auto lg:h-[200px] relative bg-linear-to-r from-yellow-400 to-orange-400 rounded-lg shadow-lg flex p-4 lg:p-10 gap-14">
            <div className="hidden lg:block lg:flex-1">
              <Image
                src={"/landing/0805.png"}
                alt="image"
                width={200}
                height={300}
                className="absolute -bottom-10 w-fit h-auto hidden lg:block"
              />
            </div>
            <div className="flex-2 flex items-center">
              <h2 className="text-white text-xl lg:text-5xl font-bold">
                {t("landing.headline")}
              </h2>
            </div>
          </div>
          <div className="w-full lg:w-[400px] text-center mx-auto bg-amber-800 mt-20 rounded-2xl shadow-lg">
            <h1 className="text-white text-2xl py-2 px-6">
              {t("landing.program")}
            </h1>
          </div>

          <div className="flex justify-between flex-col lg:flex-row gap-4 mt-20">
            <div className="min-h-lg">
              <Image
                src={"/landing/0831.png"}
                alt="image"
                width={200}
                height={300}
                className="rounded-t-2xl w-full"
              />
              <div className="bg-amber-800 text-white min-h-[70px] rounded-b-2xl text-lg font-bold p-2">
                <p className="b3bc">{t("landing.kumys")}</p>
              </div>
            </div>
            <div className="min-h-lg">
              <Image
                src={"/landing/0832.png"}
                alt="image"
                width={200}
                height={300}
                className="rounded-t-2xl w-full"
              />
              <div className="bg-amber-800 text-white min-h-[70px] rounded-b-2xl text-lg font-bold p-2">
                <p className="b3bc">{t("landing.horse")}</p>
              </div>
            </div>
            <div className="min-h-lg">
              <Image
                src={"/landing/0833.png"}
                alt="image"
                width={200}
                height={300}
                className="rounded-t-2xl w-full"
              />
              <div className="bg-amber-800 text-white min-h-[70px] rounded-b-2xl text-lg font-bold p-2">
                <p className="b3bc">{t("landing.showoff")}</p>
              </div>
            </div>
            <div className="min-h-lg">
              <Image
                src={"/landing/0834.png"}
                alt="image"
                width={200}
                height={300}
                className="rounded-t-2xl w-full"
              />
              <div className="bg-amber-800 text-white min-h-[70px] rounded-b-2xl text-lg font-bold p-2">
                <p className="b3bc">{t("landing.participants")}</p>
              </div>
            </div>
            <div className="min-h-lg">
              <Image
                src={"/landing/0835.png"}
                alt="image"
                width={200}
                height={300}
                className="rounded-t-2xl w-full"
              />
              <div className="bg-amber-800 text-white min-h-[70px] rounded-b-2xl text-lg font-bold p-2">
                <p className="b3bc">{t("landing.food")}</p>
              </div>
            </div>
          </div>

          <div className="hidden lg:flex bg-[url('/landing/0813.png')] w-full py-16 gap-4 mt-20 justify-end items-center bg-cover rounded-2xl">
            <div className="w-[40%] text-right mr-20">
              <h1 className="text-white text-5xl py-2 font-extrabold px-6">
                ЭТНО-АУЫЛ
              </h1>
              <p className="text-white text-lg py-2 px-6">
                Фестивальде этно ауыл ұсынылады, мұнда келушілер қазақ
                мәдениетінің дәстүрлеріне толықтай бойлап, ғасырлар бойы
                сақталып келе жатқан қолөнер көрмесімен танысады. Этно ауылдың
                әр бұрышы өз тарихын айтып, ұмытылмас әсер қалдырады.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-map-section p-12 lg:p-20">
          <h1 className="text-[#d54013] text-center text-2xl lg:text-5xl font-extrabold mb-20">
            {t("landing.sport")}
          </h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-y-[30px] md:gap-y-[70px] md:gap-x-[150px] my-[30px]">
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0821.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                АСАУ ҮЙРЕТУ
              </p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0822.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                ШАЛМА САЛУ
              </p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0823.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                АУДАРЫСПАҚ
              </p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0824.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                ҚҰМАЙ ТАЗЫ САЙЫСЫ
              </p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0825.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                ҚОШҚАР СҮЗІСТІРУ
              </p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <Image
                className="block_5_img"
                src="/landing/0826.png"
                width={150}
                height={150}
                alt="image"
              />
              <p className="text-[#d54013] font-extrabold mt-4 text-lg">
                МЕШКЕЙЛЕР ЖАРЫСЫ
              </p>
            </div>
          </div>
        </div>

        <div className="bg-map-section w-full h-auto py-8 bg-cover">
          <div className="w-[90%] mx-auto flex flex-col gap-8">
            <div className="font-extrabold text-orange">
              <div className="flex gap-3 items-center">
                <Image
                  src={"/pin.svg"}
                  alt="pin"
                  width={200}
                  height={200}
                  className="w-[35px] h-[35px]"
                />
                <div>
                  <p className="text-md font-bold uppercase">
                    {t("home.astana")}
                  </p>
                  <p className="text-md font-bold uppercase">
                    {t("home.hippodrome")}
                  </p>
                </div>
              </div>
            </div>
            <div className="border-orange border-2 rounded-4xl overflow-hidden">
              <YMaps
                query={{
                  lang: "ru_RU",
                  apikey: "536168cc-8dbb-4923-a06f-9a6bd5a9cf15",
                }}
              >
                <Map
                  defaultState={{ center: [51.0698, 71.3868], zoom: 15 }}
                  className=" w-full h-[300px]"
                >
                  <Placemark
                    geometry={[51.0698, 71.3868]}
                    options={{ iconColor: "#f00" }}
                  />
                </Map>
              </YMaps>
            </div>
          </div>
        </div>

        <Image
          priority
          src={"/map_section2.png"}
          alt="pin"
          width={200}
          height={200}
          className="bg-contain w-full h-auto"
        />
        <div id="contacts" className="scroll-mt-8">
          <Footer />
        </div>
      </div>
    </main>
  );
}
