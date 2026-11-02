import Link from "next/link";

export default function NotFound() {
  return (
    <section className="flex flex-col items-center gap-3 p-10 text-center">
      <h1 className="text-3xl font-bold">Page not found</h1>
      <p className="text-muted">We could not find that page.</p>
      <Link href="/" className="rounded-control bg-brand px-4 py-2 text-brand-foreground">
        Back to Overview
      </Link>
    </section>
  );
}
