import Link from "next/link";

import { ResetPasswordForm } from "./ui";

export default function ResetPasswordPage() {
  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Set a new password</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose a strong password you haven&apos;t used before on this site.
        </p>
      </div>
      <ResetPasswordForm />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary underline underline-offset-4">
          Back to log in
        </Link>
      </p>
    </>
  );
}
