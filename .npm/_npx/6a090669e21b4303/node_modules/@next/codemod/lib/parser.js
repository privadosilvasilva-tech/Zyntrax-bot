"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createParserFromPath = createParserFromPath;
const jscodeshift_1 = __importDefault(require("jscodeshift"));
const babylon_1 = __importDefault(require("jscodeshift/parser/babylon"));
const tsOptions_1 = __importDefault(require("jscodeshift/parser/tsOptions"));
const dtsOptions = {
    ...tsOptions_1.default,
    plugins: [
        ...tsOptions_1.default.plugins.filter((plugin) => plugin !== 'typescript'),
        ['typescript', { dts: true }],
    ],
};
function createParserFromPath(filePath) {
    const isDeclarationFile = /\.d\.(m|c)?ts$/.test(filePath);
    if (isDeclarationFile) {
        return jscodeshift_1.default.withParser((0, babylon_1.default)(dtsOptions));
    }
    // jsx is allowed in .js files, feed them into the tsx parser.
    // tsx parser :.js, .jsx, .tsx
    // ts parser: .ts, .mts, .cts
    const isTsFile = /\.(m|c)?.ts$/.test(filePath);
    return isTsFile ? jscodeshift_1.default.withParser('ts') : jscodeshift_1.default.withParser('tsx');
}
//# sourceMappingURL=parser.js.map