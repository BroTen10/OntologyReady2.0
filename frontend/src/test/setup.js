import '@testing-library/jest-dom/vitest';

// jsdom localStorage polyfill
const storage = {};
globalThis.localStorage = {
  getItem: (key) => storage[key] ?? null,
  setItem: (key, value) => { storage[key] = String(value); },
  removeItem: (key) => { delete storage[key]; },
  clear: () => { Object.keys(storage).forEach((k) => delete storage[k]); },
};
