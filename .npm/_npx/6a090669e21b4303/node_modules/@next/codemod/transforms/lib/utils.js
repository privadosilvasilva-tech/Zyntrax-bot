"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isNextConfigFile = isNextConfigFile;
const node_path_1 = __importDefault(require("node:path"));
function isNextConfigFile(file) {
    const parsed = node_path_1.default.parse(file.path || '/');
    return (parsed.base === 'next.config.js' ||
        parsed.base === 'next.config.ts' ||
        parsed.base === 'next.config.mjs' ||
        parsed.base === 'next.config.cjs');
}
//# sourceMappingURL=utils.js.map