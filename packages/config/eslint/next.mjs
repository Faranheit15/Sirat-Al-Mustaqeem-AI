import base from "./base.mjs";

export default [
  ...base,
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-misused-promises": "off"
    }
  }
];
