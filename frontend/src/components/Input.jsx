import React from "react";

// @ts-ignore
const Input = (props) => {
  return (
    <input
      {...props}
      className={`border-1 w-full h-[60px] border-white text-white py-2 px-4 rounded-2xl outline-none text-lg ${props.className}`}
    />
  );
};

export default Input;
