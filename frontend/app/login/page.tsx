import Link from "next/link";
import { LoginForm } from "./ui";

export default function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-16">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Log in</h1>
        <p className="mt-1 text-sm text-[color:var(--muted)]">
          Use your email and password from sign up.
        </p>
      </div>
      <LoginForm nextPathPromise={searchParams} />
      <p className="mt-6 text-center text-sm text-[color:var(--muted)]">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="font-medium text-[color:var(--accent)] underline">
          Sign up
        </Link>
      </p>
    </main>
  );
}
