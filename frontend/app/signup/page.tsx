import Link from "next/link";
import { SignupForm } from "./ui";

export default function SignupPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Sign up</h1>
        <p className="mt-1 text-sm text-[color:var(--muted)]">
          Create an account. If email confirmation is enabled in Supabase,
          check your inbox before signing in.
        </p>
      </div>
      <SignupForm />
      <p className="mt-6 text-center text-sm text-[color:var(--muted)]">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-[color:var(--accent)] underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
