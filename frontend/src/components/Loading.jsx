import React from "react";
import clsx from "clsx";

export default function Loading({ color = "white", size = 10 }) {
  return (
    <div
      className={clsx(
        `w-${size} h-${size}`,
        "border-4",
        `border-${color}`,
        "border-t-transparent rounded-full animate-spin"
      )}
    />
  );
}
