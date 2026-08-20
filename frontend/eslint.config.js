import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import eslintConfigPrettier from 'eslint-config-prettier'

export default tseslint.config(
  // docs/figma-export는 마이그레이션 대상 프로토타입 원본이라 린트 대상에서 제외한다
  // (frontend/CLAUDE.md §3 "피그마 코드 이관 매핑" 참고 — src/로 옮기며 다시 작성한다).
  // public/mockServiceWorker.js는 `npx msw init`이 생성한 서드파티 파일이라 제외한다.
  { ignores: ['dist', 'docs', 'public'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  eslintConfigPrettier,
)
