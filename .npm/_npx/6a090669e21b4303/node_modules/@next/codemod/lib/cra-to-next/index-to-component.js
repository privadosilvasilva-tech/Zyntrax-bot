"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.indexContext = void 0;
exports.default = transformer;
const parser_1 = require("../parser");
exports.indexContext = {
    multipleRenderRoots: false,
    nestedRender: false,
};
function transformer(file, _api, options) {
    const j = (0, parser_1.createParserFromPath)(file.path);
    const root = j(file.source);
    let hasModifications = false;
    let foundReactRender = 0;
    let hasRenderImport = false;
    let defaultReactDomImport;
    root.find(j.ImportDeclaration).forEach((path) => {
        if (path.node.source.value === 'react-dom') {
            return path.node.specifiers.forEach((specifier) => {
                if (specifier.local.name === 'render') {
                    hasRenderImport = true;
                }
                if (specifier.type === 'ImportDefaultSpecifier') {
                    defaultReactDomImport = specifier.local.name;
                }
            });
        }
        return false;
    });
    root
        .find(j.CallExpression)
        .filter((path) => {
        const { node } = path;
        let found = false;
        if (defaultReactDomImport &&
            node.callee.type === 'MemberExpression' &&
            node.callee.object.name === defaultReactDomImport &&
            node.callee.property.name === 'render') {
            found = true;
        }
        if (hasRenderImport && node.callee.name === 'render') {
            found = true;
        }
        if (found) {
            foundReactRender++;
            hasModifications = true;
            if (!Array.isArray(path.parentPath?.parentPath?.value)) {
                exports.indexContext.nestedRender = true;
                return false;
            }
            const newNode = j.exportDefaultDeclaration(j.functionDeclaration(j.identifier('NextIndexWrapper'), [], j.blockStatement([
                j.returnStatement(
                // TODO: remove React.StrictMode wrapper and use
                // next.config.js option instead?
                path.node.arguments.find((a) => a.type === 'JSXElement')),
            ])));
            path.parentPath.insertBefore(newNode);
            return true;
        }
        return false;
    })
        .remove();
    exports.indexContext.multipleRenderRoots = foundReactRender > 1;
    hasModifications =
        hasModifications &&
            !exports.indexContext.nestedRender &&
            !exports.indexContext.multipleRenderRoots;
    // TODO: move function passed to reportWebVitals if present to
    // _app reportWebVitals and massage values to expected shape
    // root.find(j.CallExpression, {
    //   callee: {
    //     name: 'reportWebVitals'
    //   }
    // }).remove()
    return hasModifications ? root.toSource(options) : null;
}
//# sourceMappingURL=index-to-component.js.map