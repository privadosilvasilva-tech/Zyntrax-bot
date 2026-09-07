"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.globalCssContext = void 0;
exports.default = transformer;
const path_1 = __importDefault(require("path"));
const parser_1 = require("../parser");
exports.globalCssContext = {
    cssImports: new Set(),
    reactSvgImports: new Set(),
};
const globalStylesRegex = /(?<!\.module)\.(css|scss|sass)$/i;
function transformer(file, _api, options) {
    const j = (0, parser_1.createParserFromPath)(file.path);
    const root = j(file.source);
    let hasModifications = false;
    root
        .find(j.ImportDeclaration)
        .filter((path) => {
        const { node: { source: { value }, }, } = path;
        if (typeof value === 'string') {
            if (globalStylesRegex.test(value)) {
                let resolvedPath = value;
                if (value.startsWith('.')) {
                    resolvedPath = path_1.default.resolve(path_1.default.dirname(file.path), value);
                }
                exports.globalCssContext.cssImports.add(resolvedPath);
                const { start, end } = path.node;
                if (!path.parentPath.node.comments) {
                    path.parentPath.node.comments = [];
                }
                path.parentPath.node.comments = [
                    j.commentLine(' ' + file.source.substring(start, end)),
                ];
                hasModifications = true;
                return true;
            }
            else if (value.endsWith('.svg')) {
                const isComponentImport = path.node.specifiers.some((specifier) => {
                    return specifier.imported?.name === 'ReactComponent';
                });
                if (isComponentImport) {
                    exports.globalCssContext.reactSvgImports.add(file.path);
                }
            }
        }
        return false;
    })
        .remove();
    return hasModifications && exports.globalCssContext.reactSvgImports.size === 0
        ? root.toSource(options)
        : null;
}
//# sourceMappingURL=global-css-transform.js.map