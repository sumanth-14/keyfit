"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { useState } from "react";
import { ApiRequestError } from "@/lib/api/client";
import { useToastStore } from "@/lib/store/toast";

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return error.detail.user_message;
  return "Something went wrong. Please try again.";
}

export default function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser session — useState prevents recreation on re-renders.
  // QueryCache/MutationCache global error handlers route API errors to the toast store
  // via getState() so we don't need a hook inside the initializer.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error) =>
            useToastStore.getState().addToast(errorMessage(error), "error"),
        }),
        mutationCache: new MutationCache({
          onError: (error) =>
            useToastStore.getState().addToast(errorMessage(error), "error"),
        }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
