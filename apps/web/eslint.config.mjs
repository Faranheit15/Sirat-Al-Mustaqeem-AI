import nextPlugin from "@next/eslint-plugin-next";
import base from "@sirat/config/eslint/next";

export default [
  ...base,
  {
    plugins: {
      "@next/next": nextPlugin
    },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules
    }
  }
];
