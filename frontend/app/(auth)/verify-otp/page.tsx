import Link from "next/link";
import { VerifyOtpForm } from "./ui";

export default function VerifyOtpPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string }>;
}) {
  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Verify your email</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter the 6-digit code we sent. Didn&apos;t get it? You can resend after the timer.
        </p>
      </div>
      <VerifyOtpForm emailPromise={searchParams} />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Wrong address?{" "}
        <Link href="/signup" className="font-medium text-primary underline underline-offset-4">
          Go back
        </Link>
      </p>
    </>
  );
}
