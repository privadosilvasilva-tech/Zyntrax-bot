"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = transformer;
const parser_1 = require("../lib/parser");
function transformer(file, _api, options) {
    const j = (0, parser_1.createParserFromPath)(file.path);
    const root = j(file.source);
    let hasChanges = false;
    // Before: import { ... } from '@next/font'
    // After: import { ... } from 'next/font'
    root
        .find(j.ImportDeclaration, {
        source: { value: '@next/font' },
    })
        .forEach((fontImport) => {
        hasChanges = true;
        fontImport.node.source = j.stringLiteral('next/font');
    });
    // Before: import { ... } from '@next/font/google'
    // After: import { ... } from 'next/font/google'
    root
        .find(j.ImportDeclaration, {
        source: { value: '@next/font/google' },
    })
        .forEach((fontImport) => {
        hasChanges = true;
        fontImport.node.source = j.stringLiteral('next/font/google');
    });
    // Before: import localFont from '@next/font/local'
    // After: import localFont from 'next/font/local'
    root
        .find(j.ImportDeclaration, {
        source: { value: '@next/font/local' },
    })
        .forEach((fontImport) => {
        hasChanges = true;
        fontImport.node.source = j.stringLiteral('next/font/local');
    });
    return hasChanges ? root.toSource(options) : file.source;
}
//# sourceMappingURL=built-in-next-font.js.map