declare function acquireVsCodeApi(): {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
};

let api: ReturnType<typeof acquireVsCodeApi> | undefined;

export function useVsCodeApi() {
  if (!api) {
    try {
      api = acquireVsCodeApi();
    } catch {
      // Running outside VS Code (e.g., in dev mode)
      api = {
        postMessage: (msg: unknown) => console.log('postMessage:', msg),
        getState: () => undefined,
        setState: (state: unknown) => console.log('setState:', state),
      };
    }
  }
  return api;
}
