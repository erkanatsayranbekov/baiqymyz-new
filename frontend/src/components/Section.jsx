import Image from "next/image";
import Footer from "~/components/Footer";
import Header from "~/components/Header";
import React, { useState } from "react";

// @ts-ignore
const Section = ({ children }) => {
  return (
    <div className="max-w-[1500px] lg:w-[1200px] mx-auto bg-white flex flex-col">
      <Header />
      <Image
        className="w-full top-0"
        height={20}
        width={500}
        alt="image"
        src="/oyu_2_small.png"
      />
      {children}
      <Footer />
    </div>
  );
};

export default Section;
