// Default company used ONLY to bootstrap an empty store on first load.
// Env-driven so no specific company is hardcoded in the app logic. If unset,
// the app starts with no selection and shows an empty state until the user searches.
export const DEFAULT_TICKER = process.env.NEXT_PUBLIC_DEFAULT_TICKER ?? "";
