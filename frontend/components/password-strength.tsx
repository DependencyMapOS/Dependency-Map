"use client";

import { Check, X } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  passwordRequirementChecks,
  passwordStrengthLabel,
  passwordStrengthScore,
} from "@/lib/password-rules";

export function PasswordStrength({ password }: { password: string }) {
  const checks = passwordRequirementChecks(password);
  const score = passwordStrengthScore(password);
  const label = passwordStrengthLabel(score);
  const pct = (score / 5) * 100;

  const items: { key: keyof typeof checks; label: string }[] = [
    { key: "minLength", label: "At least 8 characters" },
    { key: "uppercase", label: "Uppercase letter" },
    { key: "lowercase", label: "Lowercase letter" },
    { key: "digit", label: "Number" },
    { key: "special", label: "Special character" },
  ];

  if (!password) return null;

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-300",
              score <= 2 && "bg-destructive",
              score === 3 && "bg-amber-500",
              score === 4 && "bg-lime-500",
              score >= 5 && "bg-emerald-500",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Password strength:{" "}
          <span className="font-medium capitalize text-foreground">{label}</span>
        </p>
      </div>
      <ul className="space-y-1 text-xs">
        {items.map(({ key, label: text }) => (
          <li key={key} className="flex items-center gap-2">
            {checks[key] ? (
              <Check className="size-3.5 shrink-0 text-emerald-500" aria-hidden />
            ) : (
              <X className="size-3.5 shrink-0 text-muted-foreground/60" aria-hidden />
            )}
            <span className={checks[key] ? "text-foreground" : "text-muted-foreground"}>
              {text}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PasswordMatchIndicator({
  password,
  confirm,
}: {
  password: string;
  confirm: string;
}) {
  if (!confirm) return null;
  const match = password === confirm && password.length > 0;
  return (
    <p
      className={cn("text-xs", match ? "text-emerald-600 dark:text-emerald-400" : "text-destructive")}
      role="status"
    >
      {match ? "Passwords match" : "Passwords must match"}
    </p>
  );
}
