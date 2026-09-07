"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = transformer;
const parser_1 = require("../lib/parser");
const importToChange = 'ImageResponse';
function transformer(file, _api) {
    const j = (0, parser_1.createParserFromPath)(file.path);
    // Find import declarations that match the pattern
    file.source = j(file.source)
        .find(j.ImportDeclaration, {
        source: {
            value: 'next/server',
        },
    })
        .forEach((path) => {
        const importSpecifiers = path.node.specifiers;
        const importNamesToChange = importSpecifiers.filter((specifier) => specifier.local.name === importToChange);
        const importsNamesRemained = importSpecifiers.filter((specifier) => specifier.local.name !== importToChange);
        // If the import includes the specified import name, create a new import for it from 'next/og'
        if (importNamesToChange.length > 0) {
            // Replace the original import with the remaining specifiers
            // path.node.specifiers = remainingSpecifiers
            const newImportStatement = j.importDeclaration(importNamesToChange, j.stringLiteral('next/og'));
            path.insertBefore(newImportStatement);
        }
        if (importsNamesRemained.length > 0) {
            const remainingSpecifiers = importSpecifiers.filter((specifier) => specifier.local.name !== importToChange);
            const nextServerRemainImportsStatement = j.importDeclaration(remainingSpecifiers, j.stringLiteral('next/server'));
            path.insertBefore(nextServerRemainImportsStatement);
        }
        j(path).remove();
    })
        .toSource();
    return file.source;
}
//# sourceMappingURL=next-og-import.js.map