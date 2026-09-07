"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = transformer;
const parser_1 = require("../lib/parser");
function transformer(file, _api) {
    if (process.env.NODE_ENV !== 'test' &&
        !/[/\\]app[/\\].*?(page|layout|route)\.[^/\\]+$/.test(file.path)) {
        return file.source;
    }
    const j = (0, parser_1.createParserFromPath)(file.path);
    const root = j(file.source);
    const runtimeExport = root.find(j.ExportNamedDeclaration, {
        declaration: {
            type: 'VariableDeclaration',
            declarations: [
                {
                    id: { name: 'runtime' },
                },
            ],
        },
    });
    if (runtimeExport.size() !== 1) {
        return file.source;
    }
    const runtimeValue = runtimeExport.find(j.StringLiteral, {
        value: 'experimental-edge',
    });
    if (runtimeValue.size() !== 1) {
        return file.source;
    }
    runtimeValue.replaceWith(j.stringLiteral('edge'));
    return root.toSource();
}
//# sourceMappingURL=app-dir-runtime-config-experimental-edge.js.map