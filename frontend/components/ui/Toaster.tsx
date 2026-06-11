"use client";

import { X } from "lucide-react";
import { useToastStore } from "@/lib/store/toast";

export default function Toaster() {
  const { toasts, removeToast } = useToastStore();
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex max-w-sm items-start gap-3 rounded-xl border px-4 py-3 shadow-lg ${
            toast.type === "error"
              ? "border-red-200 bg-red-50 text-red-800"
              : toast.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-line bg-paper-raised text-ink"
          }`}
        >
          <p className="flex-1 text-sm leading-snug">{toast.message}</p>
          <button
            type="button"
            onClick={() => removeToast(toast.id)}
            className="mt-0.5 shrink-0 opacity-60 hover:opacity-100"
            aria-label="Dismiss"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
