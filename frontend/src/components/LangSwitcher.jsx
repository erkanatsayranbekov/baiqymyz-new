"use client";

import { useState } from "react";
import i18n from "~/lib/i18n";

const LanguageSwitcher = () => {
  const [lang, setLang] = useState(i18n.language || "kz");

  // @ts-ignore
  const handleLangChange = (e) => {
    const selectedLang = e.target.value;
    i18n.changeLanguage(selectedLang);
    setLang(selectedLang);
  };
  return (
    <select
      name="lang"
      id="language"
      className="outline-none border-none text-white bg-orange px-4 py-2 rounded"
      value={lang}
      onChange={handleLangChange}
    >
      <option value="ru">Рус</option>
      <option value="kz">Қаз</option>
    </select>
  );
};

export default LanguageSwitcher;
