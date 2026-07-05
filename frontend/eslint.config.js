export default [
  {
    files: ['src/**/*.{js,jsx}'],
    rules: {
      'no-unused-vars': 'warn',
      'no-undef': 'error',
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { window: 'readonly', document: 'readonly', console: 'readonly', alert: 'readonly', URL: 'readonly' },
    },
  },
  { ignores: ['dist/'] },
]
