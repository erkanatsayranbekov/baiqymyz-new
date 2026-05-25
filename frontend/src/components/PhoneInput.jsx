import React, { useEffect, useRef } from "react";
import IMask from "imask";
import { on } from "events";

// @ts-ignore
const PhoneInput = ({ maskOptions, onAccept, ...props }) => {
  const inputRef = useRef(null);
  const maskRef = useRef(null);

  useEffect(() => {
    if (inputRef.current && maskOptions) {
      // @ts-ignore
      maskRef.current = IMask(inputRef.current, maskOptions);

      if (onAccept) {
        // @ts-ignore
        maskRef.current.on("accept", () => {
          // @ts-ignore
          onAccept(maskRef.current.unmaskedValue);
        });
      }

      // return () => {
      //   maskRef.current?.destroy();
      // };
    }
  }, [maskOptions, onAccept]);

  return (
    <input
      ref={inputRef}
      className="border-1 w-full h-[60px] border-white text-white py-2 px-4 rounded-2xl outline-none text-lg"
      {...props}
    />
  );
};

export default PhoneInput;
