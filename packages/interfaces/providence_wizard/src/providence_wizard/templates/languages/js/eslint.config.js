export default [
  {
    ignores: ['dist', 'node_modules', 'coverage'],
  },
  {
    files: ['src/**/*.ts', 'src/**/*.js'],
    languageOptions: {
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        project: './tsconfig.json',
      },
    },
    plugins: {
      '@typescript-eslint': require('@typescript-eslint/eslint-plugin'),
    },
    rules: {
      '@typescript-eslint/explicit-function-return-types': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-member-accessibility': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
];
