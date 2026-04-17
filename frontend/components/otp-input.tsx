"use client";

import { useRef } from "react";

import { Input } from "@/components/ui/input";
import { normalizeOtp, OTP_LENGTH } from "@/lib/otp-utils";
import { cn } from "@/lib/utils";

export function OtpInput({
  value,
  onChange,
  disabled,
  idPrefix = "otp",
}: {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  idPrefix?: string;
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const clean = normalizeOtp(value);
  const cells = Array.from({ length: OTP_LENGTH }, (_, i) => clean[i] ?? "");

  const commit = (next: string) => {
    onChange(normalizeOtp(next));
  };

  return (
    <div
      className="flex justify-center gap-2"
      onPaste={(e) => {
        e.preventDefault();
        const pasted = normalizeOtp(e.clipboardData.getData("text"));
        commit(pasted);
        refs.current[Math.min(pasted.length, OTP_LENGTH - 1)]?.focus();
      }}
    >
      {cells.map((ch, i) => (
        <Input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          id={`${idPrefix}-${i}`}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          maxLength={1}
          disabled={disabled}
          value={ch}
          onChange={(e) => {
            const d = e.target.value.replace(/\D/g, "").slice(-1);
            if (!d) {
              const left = clean.slice(0, i);
              const right = clean.slice(i + 1);
              commit(left + right);
              return;
            }
            const next = clean.slice(0, i) + d + clean.slice(i + 1);
            commit(next);
            if (d && i < OTP_LENGTH - 1) refs.current[i + 1]?.focus();
          }}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !cells[i] && i > 0) {
              refs.current[i - 1]?.focus();
            }
            if (e.key === "ArrowLeft" && i > 0) refs.current[i - 1]?.focus();
            if (e.key === "ArrowRight" && i < OTP_LENGTH - 1) refs.current[i + 1]?.focus();
          }}
          className={cn("h-11 w-10 px-0 text-center text-lg tabular-nums")}
          aria-label={`Digit ${i + 1} of ${OTP_LENGTH}`}
        />
      ))}
    </div>
  );
}
