import Link from "next/link";
import { LoginForm } from "./ui";

export default function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Log in</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Use your email and password from sign up.
        </p>
      </div>
      <LoginForm nextPathPromise={searchParams} />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="font-medium text-primary underline underline-offset-4">
          Sign up
        </Link>
      </p>
    </>
  );
}
