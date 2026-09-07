"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isReactHookName = exports.TARGET_PROP_NAMES = exports.TARGET_NAMED_EXPORTS = exports.TARGET_ROUTE_EXPORTS = exports.NEXT_CODEMOD_ERROR_PREFIX = exports.NEXTJS_ENTRY_FILES = void 0;
exports.isFunctionType = isFunctionType;
exports.isMatchedFunctionExported = isMatchedFunctionExported;
exports.determineClientDirective = determineClientDirective;
exports.isPromiseType = isPromiseType;
exports.turnFunctionReturnTypeToAsync = turnFunctionReturnTypeToAsync;
exports.insertReactUseImport = insertReactUseImport;
exports.generateUniqueIdentifier = generateUniqueIdentifier;
exports.isFunctionScope = isFunctionScope;
exports.findClosetParentFunctionScope = findClosetParentFunctionScope;
exports.getFunctionPathFromExportPath = getFunctionPathFromExportPath;
exports.wrapParentheseIfNeeded = wrapParentheseIfNeeded;
exports.insertCommentOnce = insertCommentOnce;
exports.getVariableDeclaratorId = getVariableDeclaratorId;
exports.findFunctionBody = findFunctionBody;
exports.containsReactHooksCallExpressions = containsReactHooksCallExpressions;
exports.isParentUseCallExpression = isParentUseCallExpression;
exports.isParentPromiseAllCallExpression = isParentPromiseAllCallExpression;
exports.NEXTJS_ENTRY_FILES = /([\\/]|^)(page|layout|route|default)\.(t|j)sx?$/;
exports.NEXT_CODEMOD_ERROR_PREFIX = '@next-codemod-error';
const NEXT_CODEMOD_IGNORE_ERROR_PREFIX = '@next-codemod-ignore';
exports.TARGET_ROUTE_EXPORTS = new Set([
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
    'HEAD',
]);
exports.TARGET_NAMED_EXPORTS = new Set([
    // For page and layout
    'generateMetadata',
    'generateViewport',
    ...exports.TARGET_ROUTE_EXPORTS,
]);
exports.TARGET_PROP_NAMES = new Set(['params', 'searchParams']);
function isFunctionType(type) {
    return (type === 'FunctionDeclaration' ||
        type === 'FunctionExpression' ||
        type === 'ArrowFunctionExpression');
}
function isMatchedFunctionExported(path, j) {
    const matchedFunctionNameFilter = (idName) => exports.TARGET_NAMED_EXPORTS.has(idName);
    const directNamedExport = j(path).closest(j.ExportNamedDeclaration, {
        declaration: {
            type: 'FunctionDeclaration',
            id: {
                name: matchedFunctionNameFilter,
            },
        },
    });
    if (directNamedExport.size() > 0) {
        return true;
    }
    // Check for default export (`export default function() {}`)
    const isDefaultExport = j(path).closest(j.ExportDefaultDeclaration).size() > 0;
    if (isDefaultExport) {
        return true;
    }
    // Look for named export elsewhere in the file (`export { <named> }`)
    const root = j(path).closestScope().closest(j.Program);
    const isNamedExport = root
        .find(j.ExportNamedDeclaration, {
        specifiers: [
            {
                type: 'ExportSpecifier',
                exported: {
                    name: matchedFunctionNameFilter,
                },
            },
        ],
    })
        .size() > 0;
    // Look for variable export but still function, e.g. `export const <named> = function() {}`,
    // also check if variable is a function or arrow function
    const isVariableExport = root
        .find(j.ExportNamedDeclaration, {
        declaration: {
            declarations: [
                {
                    type: 'VariableDeclarator',
                    id: {
                        type: 'Identifier',
                        name: matchedFunctionNameFilter,
                    },
                    init: {
                        type: isFunctionType,
                    },
                },
            ],
        },
    })
        .size() > 0;
    if (isVariableExport)
        return true;
    return isNamedExport;
}
// directive is not parsed into AST, so we need to manually find it
// by going through the tokens. Use the 1st string token as the directive
function determineClientDirective(root, j) {
    const { program } = root.get().node;
    const directive = program.directives[0];
    if (j.Directive.check(directive)) {
        return directive.value.value === 'use client';
    }
    return false;
}
function isPromiseType(typeAnnotation) {
    return (typeAnnotation.type === 'TSTypeReference' &&
        typeAnnotation.typeName.name === 'Promise');
}
function turnFunctionReturnTypeToAsync(node, j) {
    if (j.FunctionDeclaration.check(node) ||
        j.FunctionExpression.check(node) ||
        j.ArrowFunctionExpression.check(node)) {
        if (node.returnType) {
            const returnTypeAnnotation = node.returnType.typeAnnotation;
            const isReturnTypePromise = isPromiseType(returnTypeAnnotation);
            // Turn <return type> to Promise<return type>
            // e.g. () => { slug: string } to () => Promise<{ slug: string }>
            // e.g. Anything to Promise<Anything>
            if (!isReturnTypePromise) {
                if (node.returnType &&
                    j.TSTypeAnnotation.check(node.returnType) &&
                    (j.TSTypeReference.check(node.returnType.typeAnnotation) ||
                        j.TSUnionType.check(node.returnType.typeAnnotation) ||
                        j.TSTypePredicate.check(node.returnType.typeAnnotation))) {
                    // Change the return type to Promise<void>
                    node.returnType.typeAnnotation = j.tsTypeReference(j.identifier('Promise'), 
                    // @ts-ignore ignore the super strict type checking on the type annotation
                    j.tsTypeParameterInstantiation([returnTypeAnnotation]));
                }
            }
        }
    }
}
function insertReactUseImport(root, j) {
    const hasReactUseImport = root
        .find(j.ImportSpecifier, {
        imported: {
            type: 'Identifier',
            name: 'use',
        },
    })
        .size() > 0;
    if (!hasReactUseImport) {
        const reactImportDeclaration = root.find(j.ImportDeclaration, {
            source: {
                value: 'react',
            },
            // Skip the type only react imports
            importKind: 'value',
        });
        if (reactImportDeclaration.size() > 0) {
            const importNode = reactImportDeclaration.get().node;
            // Add 'use' to existing 'react' import declaration
            importNode.specifiers.push(j.importSpecifier(j.identifier('use')));
        }
        else {
            // Final all type imports to 'react'
            if (reactImportDeclaration.size() > 0) {
                reactImportDeclaration
                    .get()
                    .node.specifiers.push(j.importSpecifier(j.identifier('use')));
            }
            else {
                // Add new import declaration for 'react' and 'use'
                root
                    .get()
                    .node.program.body.unshift(j.importDeclaration([j.importSpecifier(j.identifier('use'))], j.literal('react')));
            }
        }
    }
}
function findSubScopeArgumentIdentifier(path, j, argName) {
    const defCount = j(path).find(j.Identifier, { name: argName }).size();
    return defCount > 0;
}
function generateUniqueIdentifier(defaultIdName, path, j) {
    let idName = defaultIdName;
    let idNameSuffix = 0;
    while (findSubScopeArgumentIdentifier(path, j, idName)) {
        idName = defaultIdName + idNameSuffix;
        idNameSuffix++;
    }
    const propsIdentifier = j.identifier(idName);
    return propsIdentifier;
}
function isFunctionScope(path, j) {
    if (!path)
        return false;
    const node = path.node;
    // Check if the node is a function (declaration, expression, or arrow function)
    return (j.FunctionDeclaration.check(node) ||
        j.FunctionExpression.check(node) ||
        j.ArrowFunctionExpression.check(node));
}
function findClosetParentFunctionScope(path, j) {
    if (!path.scope)
        return null;
    let parentFunctionPath = path.scope.path;
    while (parentFunctionPath && !isFunctionScope(parentFunctionPath, j)) {
        parentFunctionPath = parentFunctionPath.parent;
    }
    return parentFunctionPath;
}
function getFunctionNodeFromBinding(bindingPath, idName, j, root) {
    const bindingNode = bindingPath.node;
    if (j.FunctionDeclaration.check(bindingNode) ||
        j.FunctionExpression.check(bindingNode) ||
        j.ArrowFunctionExpression.check(bindingNode)) {
        return bindingPath;
    }
    else if (j.VariableDeclarator.check(bindingNode)) {
        const init = bindingNode.init;
        // If the initializer is a function (arrow or function expression), record it
        if (j.FunctionExpression.check(init) ||
            j.ArrowFunctionExpression.check(init)) {
            return bindingPath.get('init');
        }
    }
    else if (j.Identifier.check(bindingNode)) {
        const variablePath = root.find(j.VariableDeclaration, {
            // declarations, each is VariableDeclarator
            declarations: [
                {
                    // VariableDeclarator
                    type: 'VariableDeclarator',
                    // id is Identifier
                    id: {
                        type: 'Identifier',
                        name: idName,
                    },
                },
            ],
        });
        if (variablePath.size()) {
            const variableDeclarator = variablePath.get()?.node?.declarations?.[0];
            if (j.VariableDeclarator.check(variableDeclarator)) {
                const init = variableDeclarator.init;
                if (j.FunctionExpression.check(init) ||
                    j.ArrowFunctionExpression.check(init)) {
                    return variablePath.get('declarations', 0, 'init');
                }
            }
        }
        const functionDeclarations = root.find(j.FunctionDeclaration, {
            id: {
                name: idName,
            },
        });
        if (functionDeclarations.size()) {
            return functionDeclarations.get();
        }
    }
    return undefined;
}
function getFunctionPathFromExportPath(exportPath, j, root, namedExportFilter) {
    // Default export
    if (j.ExportDefaultDeclaration.check(exportPath.node)) {
        const { declaration } = exportPath.node;
        if (declaration) {
            if (j.FunctionDeclaration.check(declaration) ||
                j.FunctionExpression.check(declaration) ||
                j.ArrowFunctionExpression.check(declaration)) {
                return exportPath.get('declaration');
            }
            else if (j.Identifier.check(declaration)) {
                const idName = declaration.name;
                if (!namedExportFilter(idName))
                    return;
                const exportBinding = exportPath.scope.getBindings()[idName]?.[0];
                if (exportBinding) {
                    return getFunctionNodeFromBinding(exportBinding, idName, j, root);
                }
            }
        }
    }
    else if (
    // Named exports
    j.ExportNamedDeclaration.check(exportPath.node)) {
        const namedExportPath = exportPath;
        // extract the named exports, name specifiers, and default specifiers
        const { declaration, specifiers } = namedExportPath.node;
        if (declaration) {
            if (j.VariableDeclaration.check(declaration)) {
                const { declarations } = declaration;
                for (const decl of declarations) {
                    if (j.VariableDeclarator.check(decl) && j.Identifier.check(decl.id)) {
                        const idName = decl.id.name;
                        if (!namedExportFilter(idName))
                            return;
                        // get bindings for each variable declarator
                        const exportBinding = namedExportPath.scope.getBindings()[idName]?.[0];
                        if (exportBinding) {
                            return getFunctionNodeFromBinding(exportBinding, idName, j, root);
                        }
                    }
                }
            }
            else if (j.FunctionDeclaration.check(declaration) ||
                j.FunctionExpression.check(declaration) ||
                j.ArrowFunctionExpression.check(declaration)) {
                const funcName = declaration.id?.name;
                if (!namedExportFilter(funcName))
                    return;
                return namedExportPath.get('declaration');
            }
        }
        if (specifiers) {
            for (const specifier of specifiers) {
                if (j.ExportSpecifier.check(specifier)) {
                    const idName = specifier.local.name;
                    if (!namedExportFilter(idName))
                        return;
                    const exportBinding = namedExportPath.scope.getBindings()[idName]?.[0];
                    if (exportBinding) {
                        return getFunctionNodeFromBinding(exportBinding, idName, j, root);
                    }
                }
            }
        }
    }
    return undefined;
}
function wrapParentheseIfNeeded(hasChainAccess, j, expression) {
    return hasChainAccess ? j.parenthesizedExpression(expression) : expression;
}
function existsComment(comments, comment) {
    const isCodemodErrorComment = comment
        .trim()
        .startsWith(exports.NEXT_CODEMOD_ERROR_PREFIX);
    let hasIgnoreComment = false;
    let hasComment = false;
    if (comments) {
        comments.forEach((commentNode) => {
            const currentComment = commentNode.value;
            if (currentComment.trim().startsWith(NEXT_CODEMOD_IGNORE_ERROR_PREFIX)) {
                hasIgnoreComment = true;
            }
            if (currentComment === comment) {
                hasComment = true;
            }
        });
        // If it's inserting codemod error comment,
        // check if there's already a @next-codemod-ignore comment.
        // if ignore comment exists, bypass the comment insertion.
        if (hasIgnoreComment && isCodemodErrorComment) {
            return true;
        }
        if (hasComment) {
            return true;
        }
    }
    return false;
}
function insertCommentOnce(node, j, comment) {
    const hasCommentInInlineComments = existsComment(node.comments, comment);
    const hasCommentInLeadingComments = existsComment(node.leadingComments, comment);
    if (!hasCommentInInlineComments && !hasCommentInLeadingComments) {
        // Always insert into inline comment
        node.comments = [j.commentBlock(comment), ...(node.comments || [])];
        return true;
    }
    return false;
}
function getVariableDeclaratorId(path, j) {
    const parent = path.parentPath;
    if (j.VariableDeclarator.check(parent.node)) {
        const id = parent.node.id;
        if (j.Identifier.check(id)) {
            return id;
        }
    }
    return undefined;
}
function findFunctionBody(path) {
    let functionBody = path.node.body;
    if (functionBody && functionBody.type === 'BlockStatement') {
        return functionBody.body;
    }
    return null;
}
const isPascalCase = (s) => /^[A-Z][a-z0-9]*$/.test(s);
const isReactHookName = (name) => 
// function name is `use`
name === 'use' ||
    // function name is `useX*`
    (name.startsWith('use') && name[3] === name[3].toUpperCase());
exports.isReactHookName = isReactHookName;
// Determine a path of function contains any React hooks call expressions.
// e.g. if there's any of those call expressions in the function body:
// use() => true
// React.use() => false
// useXxxx() => true
// Foo.use() => true
// Foo.useXxxx() => true
function containsReactHooksCallExpressions(path, j) {
    const hasReactHooks = j(path)
        .find(j.CallExpression)
        .filter((callPath) => {
        // It's matching:
        // - use(<callPath>) => true
        // - useX*(<callPath>) => true
        const isUseHookOrReactHookCall = j.Identifier.check(callPath.value.callee) &&
            (0, exports.isReactHookName)(callPath.value.callee.name);
        // It's matching member access:
        // - React.use(<callPath>) => true
        // - Foo.useFoo(<callPath>) => true
        // - foo.useFoo(<callPath>) => false
        // - foo.use(<callPath>) => false
        const isReactUseCall = j.MemberExpression.check(callPath.value.callee) &&
            j.Identifier.check(callPath.value.callee.object) &&
            j.Identifier.check(callPath.value.callee.property) &&
            isPascalCase(callPath.value.callee.object.name) &&
            (0, exports.isReactHookName)(callPath.value.callee.property.name);
        return isUseHookOrReactHookCall || isReactUseCall;
    })
        .size() > 0;
    return hasReactHooks;
}
// Capture the parent of the current path is wrapped by `use()` call expression
// e.g.
// use(<path>) => true
// use2(<path>) => false
// React.use(<path>) => true
// Robust.use(<path>) => false
function isParentUseCallExpression(path, j) {
    const isParentUseCall = 
    // member access parentPath is argument
    j.CallExpression.check(path.parent.value) &&
        // member access is first argument
        path.parent.value.arguments[0] === path.value &&
        path.parent.value.arguments.length === 1 &&
        // function name is `use`
        j.Identifier.check(path.parent.value.callee) &&
        path.parent.value.callee.name === 'use';
    const isParentReactUseCall = 
    // member access parentPath is argument
    j.CallExpression.check(path.parent.value) &&
        // member access is first argument
        path.parent.value.arguments[0] === path.value &&
        path.parent.value.arguments.length === 1 &&
        // function name is `use`
        j.MemberExpression.check(path.parent.value.callee) &&
        j.Identifier.check(path.parent.value.callee.object) &&
        path.parent.value.callee.object.name === 'React' &&
        j.Identifier.check(path.parent.value.callee.property) &&
        path.parent.value.callee.property.name === 'use';
    return isParentUseCall || isParentReactUseCall;
}
// Determine if a path is wrapped by `Promise.all()`
// e.g.
// Promise.all(<path>) => true
// Promise.allSettled(<path>) => false
function isParentPromiseAllCallExpression(path, j) {
    const argsParent = path.parent;
    const callParent = argsParent?.parent;
    if (argsParent &&
        callParent &&
        j.ArrayExpression.check(argsParent.value) &&
        j.CallExpression.check(callParent.value) &&
        j.MemberExpression.check(callParent.value.callee) &&
        j.Identifier.check(callParent.value.callee.object) &&
        callParent.value.callee.object.name === 'Promise' &&
        j.Identifier.check(callParent.value.callee.property) &&
        callParent.value.callee.property.name === 'all') {
        return true;
    }
    return false;
}
//# sourceMappingURL=utils.js.map