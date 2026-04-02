"use client";

import { motion } from "framer-motion";
import {
  GitBranch,
  LayoutDashboard,
  Radar,
  UsersRound,
  Zap,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.45, type: "spring" as const, stiffness: 120 },
  }),
};

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-0 h-[480px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-b from-primary/10 via-transparent to-transparent blur-3xl dark:from-primary/20" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--border)/0.35)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border)/0.35)_1px,transparent_1px)] [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black,transparent)] bg-[size:48px_48px]" />
      </div>

      <main>
        <section className="mx-auto max-w-6xl px-4 pb-24 pt-16 sm:px-6 sm:pt-24">
          <motion.div
            initial="hidden"
            animate="visible"
            className="mx-auto max-w-3xl text-center"
          >
            <motion.p
              custom={0}
              variants={fadeUp}
              className="mb-4 text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground"
            >
              Architecture intelligence
            </motion.p>
            <motion.h1
              custom={1}
              variants={fadeUp}
              className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl"
            >
              Know the blast radius
              <span className="block text-muted-foreground">before it breaks someone else.</span>
            </motion.h1>
            <motion.p
              custom={2}
              variants={fadeUp}
              className="mx-auto mt-6 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg"
            >
              Dependency diffs, impact analysis, and reviewer routing for GitHub teams—pre-CI
              signal without the noise.
            </motion.p>
            <motion.div
              custom={3}
              variants={fadeUp}
              className="mt-10 flex flex-wrap items-center justify-center gap-3"
            >
              <Button size="lg" asChild className="shadow-md transition-transform hover:scale-[1.02]">
                <Link href="/signup">Get started</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/login">Log in</Link>
              </Button>
            </motion.div>
          </motion.div>
        </section>

        <section className="border-t border-border/60 bg-card/30 py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <motion.h2
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4 }}
              className="text-center text-2xl font-semibold tracking-tight"
            >
              Built for fast-moving teams
            </motion.h2>
            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  icon: Radar,
                  title: "Blast radius",
                  desc: "See what a change touches upstream—before CI finishes.",
                },
                {
                  icon: GitBranch,
                  title: "Dependency diffs",
                  desc: "Edges added or removed between base and head, not buried in lockfiles.",
                },
                {
                  icon: LayoutDashboard,
                  title: "Drift awareness",
                  desc: "Surface branch overlap and structural divergence early.",
                },
                {
                  icon: UsersRound,
                  title: "Reviewer routing",
                  desc: "CODEOWNERS and ownership hints to reach the right people.",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-40px" }}
                  transition={{ delay: i * 0.06, duration: 0.4, type: "spring" }}
                >
                  <Card className="h-full border-border/80 transition-shadow hover:shadow-md">
                    <CardHeader>
                      <item.icon className="mb-2 size-8 text-primary" aria-hidden />
                      <CardTitle className="text-lg">{item.title}</CardTitle>
                      <CardDescription className="text-sm">{item.desc}</CardDescription>
                    </CardHeader>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="mx-auto max-w-2xl text-center"
            >
              <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
              <p className="mt-2 text-muted-foreground">Three steps from install to insight.</p>
            </motion.div>
            <ol className="mx-auto mt-12 grid max-w-4xl gap-8 md:grid-cols-3">
              {[
                { step: "1", title: "Connect repo", body: "Install the GitHub app and link your organization." },
                { step: "2", title: "Analyze PRs", body: "Webhooks and API triggers build graphs at each push." },
                { step: "3", title: "See impact", body: "Blast radius, diffs, and suggested reviewers in one view." },
              ].map((s, i) => (
                <motion.li
                  key={s.step}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="relative rounded-xl border border-border bg-card p-6 text-left shadow-sm"
                >
                  <span className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                    {s.step}
                  </span>
                  <h3 className="mt-4 font-semibold">{s.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{s.body}</p>
                </motion.li>
              ))}
            </ol>
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="mt-12 flex justify-center"
            >
              <Card className="max-w-lg border-dashed">
                <CardHeader className="flex flex-row items-center gap-3">
                  <Zap className="size-8 shrink-0 text-amber-500" />
                  <div>
                    <CardTitle className="text-base">Pre-CI API</CardTitle>
                    <CardDescription>
                      Call the same summary engine from Actions or local CLIs—before heavy CI spend.
                    </CardDescription>
                  </div>
                </CardHeader>
              </Card>
            </motion.div>
          </div>
        </section>

        <footer className="border-t border-border py-10">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} Dependency Map OS
            </p>
            <div className="flex items-center gap-4">
              <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground">
                Log in
              </Link>
              <Link href="/signup" className="text-sm text-muted-foreground hover:text-foreground">
                Sign up
              </Link>
              <ThemeToggle />
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
