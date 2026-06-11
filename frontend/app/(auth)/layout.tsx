import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="px-6 py-6">
        <Link
          href="/"
          className="font-serif text-xl font-semibold tracking-tight text-ink"
        >
          Keyfit
        </Link>
      </header>
      <div className="flex flex-1 items-center justify-center px-4 pb-16">
        {children}
      </div>
    </div>
  );
}
