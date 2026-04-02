"use client";

import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { toast } from "sonner";

import { OTP_LENGTH, OtpInput } from "@/components/otp-input";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

const RESEND_COOLDOWN_SEC = 60;

export function VerifyOtpForm({
  emailPromise,
}: {
  emailPromise: Promise<{ email?: string }>;
}) {
  const { email: rawEmail } = use(emailPromise);
  const email = rawEmail ? decodeURIComponent(rawEmail) : "";
  const router = useRouter();
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SEC);
  const [canResend, setCanResend] = useState(false);

  useEffect(() => {
    if (cooldown <= 0) {
      setCanResend(true);
      return;
    }
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  useEffect(() => {
    if (!email) {
      toast.error("Email missing. Start from sign up.");
      router.replace("/signup");
    }
  }, [email, router]);

  async function handleVerify() {
    if (token.length !== OTP_LENGTH) {
      toast.error("Enter the full 6-digit code.");
      return;
    }
    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.verifyOtp({
      email,
      token,
      type: "signup",
    });
    setLoading(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Email verified. Welcome!");
    router.push("/dashboard");
    router.refresh();
  }

  async function handleResend() {
    if (!canResend || !email) return;
    setCanResend(false);
    setCooldown(RESEND_COOLDOWN_SEC);
    const supabase = createClient();
    const { error } = await supabase.auth.resend({
      type: "signup",
      email,
    });
    if (error) {
      toast.error(error.message);
      setCanResend(true);
      setCooldown(0);
      return;
    }
    toast.success("New code sent.");
  }

  if (!email) return null;

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        Code sent to <span className="font-medium text-foreground">{email}</span>
      </p>
      <OtpInput value={token} onChange={setToken} disabled={loading} />
      <Button type="button" disabled={loading || token.length !== OTP_LENGTH} onClick={handleVerify}>
        {loading ? "Verifying…" : "Verify"}
      </Button>
      <div className="text-center text-sm">
        {canResend ? (
          <button
            type="button"
            className="font-medium text-primary underline underline-offset-4"
            onClick={handleResend}
          >
            Resend code
          </button>
        ) : (
          <p className="text-muted-foreground">Resend available in {cooldown}s</p>
        )}
      </div>
    </div>
  );
}
