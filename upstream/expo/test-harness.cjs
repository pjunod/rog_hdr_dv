// Focused regression runner; this does not replace Expo's package checks.
const path = require('node:path');
if (!process.argv[2]) {
  throw new Error('Pass the prepared Expo source checkout as the first argument.');
}
const root = path.resolve(process.argv[2]);
require('jest').run([
  '--runInBand',
  '--config',
  JSON.stringify({
    rootDir: root,
    testMatch: ['**/withAndroidSplashStylesApi-test.ts'],
    transform: {
      '^.+\\.tsx?$': [
        require.resolve('babel-jest'),
        {
          presets: [require.resolve('@babel/preset-typescript')],
          plugins: [require.resolve('@babel/plugin-transform-modules-commonjs')],
        },
      ],
    },
  }),
]);
