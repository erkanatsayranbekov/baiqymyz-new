"use client";
import Image from "next/image";

function Footer() {
  return (
    <footer className="bg-teal rounded-t-3xl flex justify-between p-8 flex-col md:flex-row items-center md:items-center gap-4 text-white">
      <div className="flex justify-between items-center w-full">
        <Image
          src="/logo_white.png"
          className="h-24 w-auto"
          height={100}
          width={100}
          alt="logo-bq"
        />
        <div>
          <div className="flex justify-around items-left gap-2 flex-col md:flex-row">
            <div className="flex gap-2">
              <Image
                className="h-6 w-6 rounded-full"
                src={"/mail_icon.png"}
                height={20}
                width={20}
                alt="Mail logo"
              />
              <p>info@baiqymyz.kz</p>
            </div>
            <div className="flex gap-2">
              <Image
                className="h-6 w-6 rounded-full"
                src={"/whatsapp_icon.png"}
                height={20}
                width={20}
                alt="Whats App logo"
              />
              <p>baiqymyz.kz</p>
            </div>
            <div className="flex gap-2">
              <Image
                className="h-6 w-6 rounded-full"
                src={"/ig_icon.png"}
                height={20}
                width={20}
                alt="Instagram logo"
              />
              <p>8-(776)-201-00-05</p>
            </div>
          </div>
        </div>
      </div>
      <div>
        <Image
          className="h-24 w-auto"
          src="/aeventkz_white.png"
          height={100}
          width={100}
          alt="logo-ae"
        />
      </div>
      <div className="text-center">Astana 2025</div>
    </footer>
  );
}

export default Footer;
