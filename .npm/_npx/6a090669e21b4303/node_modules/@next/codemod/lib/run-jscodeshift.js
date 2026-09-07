"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = runJscodeshift;
// @ts-ignore internal module
const Runner_1 = __importDefault(require("jscodeshift/src/Runner"));
function runJscodeshift(transformerPath, flags, files) {
    // we run jscodeshift in the same process to be able to
    // share state between the main CRA transform and sub-transforms
    return Runner_1.default.run(transformerPath, files, {
        ignorePattern: [
            '**/node_modules/**',
            '**/.next/**',
            '**/build/**',
            // test files
            '**/*.test.*',
            '**/*.spec.*',
            '**/__tests__/**',
            '**/__mocks__/**',
        ],
        extensions: 'tsx,ts,jsx,js',
        parser: 'tsx',
        verbose: 2,
        runInBand: true,
        ...flags,
    });
}
//# sourceMappingURL=run-jscodeshift.js.map