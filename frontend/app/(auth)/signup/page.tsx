import Link from "next/link";
import { SignupForm } from "./ui";

export default function SignupPage() {
  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Sign up</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Create your account. We&apos;ll email you a code to verify.
        </p>
      </div>
      <SignupForm />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary underline underline-offset-4">
          Log in
        </Link>
      </p>
    </>
  );
}
