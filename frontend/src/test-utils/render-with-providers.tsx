import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import { type ReactElement, type ReactNode } from "react";

export function makeTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface ProviderProps {
  client?: QueryClient;
  children: ReactNode;
}

function TestProviders({ client, children }: ProviderProps) {
  const queryClient = client ?? makeTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  client?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {},
) {
  const { client, ...rest } = options;
  return render(ui, {
    wrapper: ({ children }) => (
      <TestProviders client={client}>{children}</TestProviders>
    ),
    ...rest,
  });
}
