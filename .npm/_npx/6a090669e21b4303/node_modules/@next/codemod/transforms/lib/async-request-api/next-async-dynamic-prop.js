"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformDynamicProps = transformDynamicProps;
const utils_1 = require("./utils");
const parser_1 = require("../../../lib/parser");
const PAGE_PROPS = 'props';
// Find all the member access of the prop, and await them
// e.g. If there's argument `props`, find all the member access of props.<name>.
// If the member access can be awaited, await them.
function awaitMemberAccessOfProp(propIdName, path, j) {
    // search the member access of the prop
    const functionBody = (0, utils_1.findFunctionBody)(path);
    const memberAccess = j(functionBody).find(j.MemberExpression, {
        object: {
            type: 'Identifier',
            name: propIdName,
        },
    });
    let hasAwaited = false;
    // await each member access
    memberAccess.forEach((memberAccessPath) => {
        const member = memberAccessPath.value;
        const memberProperty = member.property;
        const isAccessingMatchedProperty = j.Identifier.check(memberProperty) &&
            utils_1.TARGET_PROP_NAMES.has(memberProperty.name);
        if (!isAccessingMatchedProperty) {
            return;
        }
        if ((0, utils_1.isParentPromiseAllCallExpression)(memberAccessPath, j)) {
            return;
        }
        // check if it's already awaited
        if (memberAccessPath.parentPath?.value.type === 'AwaitExpression') {
            return;
        }
        const parentScopeOfMemberAccess = (0, utils_1.findClosetParentFunctionScope)(memberAccessPath, j);
        // When the parent scope is sync, and it's also not the function itself, which means it's not able to convert to async.
        if (parentScopeOfMemberAccess &&
            !parentScopeOfMemberAccess.value?.async &&
            parentScopeOfMemberAccess.node !== path.node) {
            // If it's not able to convert, add a comment to the prop access to warn the user
            // e.g. the parent scope is sync, await keyword can't be applied
            const comment = ` ${utils_1.NEXT_CODEMOD_ERROR_PREFIX} '${propIdName}.${memberProperty.name}' is accessed without awaiting.`;
            (0, utils_1.insertCommentOnce)(member, j, comment);
            return;
        }
        const awaitedExpr = j.awaitExpression(member);
        const awaitMemberAccess = (0, utils_1.wrapParentheseIfNeeded)(true, j, awaitedExpr);
        memberAccessPath.replace(awaitMemberAccess);
        hasAwaited = true;
    });
    const hasReactHooksUsage = (0, utils_1.containsReactHooksCallExpressions)(path.get('body'), j);
    // If there's any awaited member access, we need to make the function async
    if (hasAwaited) {
        if (path.value.async === false && !hasReactHooksUsage) {
            path.value.async = true;
            (0, utils_1.turnFunctionReturnTypeToAsync)(path.value, j);
        }
    }
    return hasAwaited;
}
function applyUseAndRenameAccessedProp(propIdName, path, j) {
    // search the member access of the prop, and rename the member access to the member value
    // e.g.
    // props.params => params
    // props.params.foo => params.foo
    // props.searchParams.search => searchParams.search
    let modified = false;
    const functionBody = (0, utils_1.findFunctionBody)(path);
    const memberAccess = j(functionBody).find(j.MemberExpression, {
        object: {
            type: 'Identifier',
            name: propIdName,
        },
    });
    const accessedNames = [];
    // rename each member access
    memberAccess.forEach((memberAccessPath) => {
        // If the member access expression is first argument of `use()`, we skip
        if ((0, utils_1.isParentUseCallExpression)(memberAccessPath, j)) {
            return;
        }
        const member = memberAccessPath.value;
        const memberProperty = member.property;
        if (j.Identifier.check(memberProperty)) {
            accessedNames.push(memberProperty.name);
        }
        else if (j.MemberExpression.check(memberProperty)) {
            let currentMember = memberProperty;
            if (j.Identifier.check(currentMember.object)) {
                accessedNames.push(currentMember.object.name);
            }
        }
        memberAccessPath.replace(memberProperty);
    });
    // If there's any renamed member access, need to call `use()` onto member access
    // e.g. ['params'] => insert `const params = use(props.params)`
    if (accessedNames.length > 0) {
        const accessedPropId = j.identifier(propIdName);
        const accessedProp = j.memberExpression(accessedPropId, j.identifier(accessedNames[0]));
        const useCall = j.callExpression(j.identifier('use'), [accessedProp]);
        const useDeclaration = j.variableDeclaration('const', [
            j.variableDeclarator(j.identifier(accessedNames[0]), useCall),
        ]);
        if (functionBody) {
            functionBody.unshift(useDeclaration);
        }
        modified = true;
    }
    return modified;
}
function commentOnMatchedReExports(root, j) {
    let modified = false;
    root.find(j.ExportNamedDeclaration).forEach((path) => {
        if (j.ExportSpecifier.check(path.value.specifiers[0])) {
            const specifiers = path.value.specifiers;
            for (const specifier of specifiers) {
                if (j.ExportSpecifier.check(specifier) &&
                    // Find matched named exports and default export
                    (utils_1.TARGET_NAMED_EXPORTS.has(specifier.exported.name) ||
                        specifier.exported.name === 'default')) {
                    if (j.Literal.check(path.value.source)) {
                        const localName = specifier.local.name;
                        const commentInserted = (0, utils_1.insertCommentOnce)(specifier, j, ` ${utils_1.NEXT_CODEMOD_ERROR_PREFIX} \`${localName}\` export is re-exported. Check if this component uses \`params\` or \`searchParams\``);
                        modified ||= commentInserted;
                    }
                    else if (path.value.source === null) {
                        const localIdentifier = specifier.local;
                        const localName = localIdentifier.name;
                        // search if local identifier is from imports
                        const importDeclaration = root
                            .find(j.ImportDeclaration)
                            .filter((importPath) => {
                            return importPath.value.specifiers.some((importSpecifier) => importSpecifier.local.name === localName);
                        });
                        if (importDeclaration.size() > 0) {
                            const commentInserted = (0, utils_1.insertCommentOnce)(specifier, j, ` ${utils_1.NEXT_CODEMOD_ERROR_PREFIX} \`${localName}\` export is re-exported. Check if this component uses \`params\` or \`searchParams\``);
                            modified ||= commentInserted;
                        }
                    }
                }
            }
        }
    });
    return modified;
}
function modifyTypes(paramTypeAnnotation, propsIdentifier, root, j) {
    let modified = false;
    if (paramTypeAnnotation && paramTypeAnnotation.typeAnnotation) {
        const typeAnnotation = paramTypeAnnotation.typeAnnotation;
        if (typeAnnotation.type === 'TSTypeLiteral') {
            const typeLiteral = typeAnnotation;
            // Find the type property for `params`
            typeLiteral.members.forEach((member) => {
                if (member.type === 'TSPropertySignature' &&
                    member.key.type === 'Identifier' &&
                    utils_1.TARGET_PROP_NAMES.has(member.key.name)) {
                    // if it's already a Promise, don't wrap it again, return
                    if (member.typeAnnotation &&
                        member.typeAnnotation.typeAnnotation &&
                        member.typeAnnotation.typeAnnotation.type === 'TSTypeReference' &&
                        member.typeAnnotation.typeAnnotation.typeName.type ===
                            'Identifier' &&
                        member.typeAnnotation.typeAnnotation.typeName.name === 'Promise') {
                        return;
                    }
                    // Wrap the `params` type in Promise<>
                    if (member.typeAnnotation &&
                        member.typeAnnotation.typeAnnotation &&
                        j.TSType.check(member.typeAnnotation.typeAnnotation)) {
                        member.typeAnnotation.typeAnnotation = j.tsTypeReference(j.identifier('Promise'), j.tsTypeParameterInstantiation([
                            member.typeAnnotation.typeAnnotation,
                        ]));
                        modified = true;
                    }
                }
            });
        }
        else if (typeAnnotation.type === 'TSTypeReference') {
            // If typeAnnotation is a type or interface, change the properties to Promise<type of property>
            // e.g. interface PageProps { params: { slug: string } } => interface PageProps { params: Promise<{ slug: string }> }
            const typeReference = typeAnnotation;
            if (typeReference.typeName.type === 'Identifier') {
                // Find the actual type of the type reference
                const foundTypes = findAllTypes(root, j, typeReference.typeName.name);
                // Deal with interfaces
                if (foundTypes.interfaces.length > 0) {
                    const interfaceDeclaration = foundTypes.interfaces[0];
                    if (interfaceDeclaration.type === 'TSInterfaceDeclaration' &&
                        interfaceDeclaration.body?.type === 'TSInterfaceBody') {
                        const typeBody = interfaceDeclaration.body.body;
                        // if it's already a Promise, don't wrap it again, return
                        // traverse the typeReference's properties, if any is in propNames, wrap it in Promise<> if needed
                        typeBody.forEach((member) => {
                            if (member.type === 'TSPropertySignature' &&
                                member.key.type === 'Identifier' &&
                                utils_1.TARGET_PROP_NAMES.has(member.key.name)) {
                                // if it's already a Promise, don't wrap it again, return
                                if (member.typeAnnotation &&
                                    member.typeAnnotation.typeAnnotation &&
                                    member.typeAnnotation?.typeAnnotation?.typeName?.name ===
                                        'Promise') {
                                    return;
                                }
                                // Wrap the prop type in Promise<>
                                if (member.typeAnnotation &&
                                    member.typeAnnotation.typeAnnotation &&
                                    // check if member name is in propNames
                                    utils_1.TARGET_PROP_NAMES.has(member.key.name)) {
                                    member.typeAnnotation.typeAnnotation = j.tsTypeReference(j.identifier('Promise'), j.tsTypeParameterInstantiation([
                                        member.typeAnnotation.typeAnnotation,
                                    ]));
                                    modified = true;
                                }
                            }
                        });
                    }
                }
                // Deal with type aliases
                if (foundTypes.typeAliases.length > 0) {
                    const typeAliasDeclaration = foundTypes.typeAliases[0];
                    if (j.TSTypeAliasDeclaration.check(typeAliasDeclaration)) {
                        const typeAlias = typeAliasDeclaration.typeAnnotation;
                        if (j.TSTypeLiteral.check(typeAlias) &&
                            typeAlias.members.length > 0) {
                            const typeLiteral = typeAlias;
                            typeLiteral.members.forEach((member) => {
                                if (j.TSPropertySignature.check(member) &&
                                    j.Identifier.check(member.key) &&
                                    utils_1.TARGET_PROP_NAMES.has(member.key.name)) {
                                    // if it's already a Promise, don't wrap it again, return
                                    if (member.typeAnnotation &&
                                        member.typeAnnotation.typeAnnotation &&
                                        member.typeAnnotation.typeAnnotation.type ===
                                            'TSTypeReference' &&
                                        member.typeAnnotation.typeAnnotation.typeName.type ===
                                            'Identifier' &&
                                        member.typeAnnotation.typeAnnotation.typeName.name ===
                                            'Promise') {
                                        return;
                                    }
                                    // Wrap the prop type in Promise<>
                                    if (member.typeAnnotation &&
                                        j.TSTypeLiteral.check(member.typeAnnotation.typeAnnotation)) {
                                        member.typeAnnotation.typeAnnotation = j.tsTypeReference(j.identifier('Promise'), j.tsTypeParameterInstantiation([
                                            member.typeAnnotation.typeAnnotation,
                                        ]));
                                        modified = true;
                                    }
                                }
                            });
                        }
                    }
                }
                if (foundTypes.imports.length > 0) {
                    // console.log('typeReference.typeName.name', typeReference.typeName.name, foundTypes)
                    // If it's React PropsWithChildren
                    if (typeReference.typeName.name === 'PropsWithChildren') {
                        const propType = typeReference.typeParameters?.params[0];
                        if (propType &&
                            j.TSTypeLiteral.check(propType) &&
                            propType.members.length > 0) {
                            const typeLiteral = propType;
                            typeLiteral.members.forEach((member) => {
                                if (j.TSPropertySignature.check(member) &&
                                    j.Identifier.check(member.key) &&
                                    utils_1.TARGET_PROP_NAMES.has(member.key.name)) {
                                    // if it's already a Promise, don't wrap it again, return
                                    if (member.typeAnnotation &&
                                        member.typeAnnotation.typeAnnotation &&
                                        member.typeAnnotation.typeAnnotation.type ===
                                            'TSTypeReference' &&
                                        member.typeAnnotation.typeAnnotation.typeName.type ===
                                            'Identifier' &&
                                        member.typeAnnotation.typeAnnotation.typeName.name ===
                                            'Promise') {
                                        return;
                                    }
                                    // Wrap the prop type in Promise<>
                                    if (member.typeAnnotation &&
                                        j.TSTypeLiteral.check(member.typeAnnotation.typeAnnotation)) {
                                        member.typeAnnotation.typeAnnotation = j.tsTypeReference(j.identifier('Promise'), j.tsTypeParameterInstantiation([
                                            member.typeAnnotation.typeAnnotation,
                                        ]));
                                        modified = true;
                                    }
                                }
                            });
                        }
                    }
                }
            }
        }
        propsIdentifier.typeAnnotation = paramTypeAnnotation;
        modified = true;
    }
    return modified;
}
function transformDynamicProps(source, _api, filePath) {
    const isEntryFile = utils_1.NEXTJS_ENTRY_FILES.test(filePath);
    if (!isEntryFile) {
        return null;
    }
    let modified = false;
    let modifiedPropArgument = false;
    const j = (0, parser_1.createParserFromPath)(filePath);
    const root = j(source);
    // Check if 'use' from 'react' needs to be imported
    let needsReactUseImport = false;
    // Based on the prop names
    // e.g. destruct `params` { slug } = params
    // e.g. destruct `searchParams `{ search } = searchParams
    let insertedDestructPropNames = new Set();
    function processAsyncPropOfEntryFile(isClientComponent) {
        // find `params` and `searchParams` in file, and transform the access to them
        function renameAsyncPropIfExisted(path, isDefaultExport) {
            const decl = path.value;
            const params = decl.params;
            let functionName = decl.id?.name;
            // If it's const <id> = function () {}, locate the <id> to get function name
            if (!decl.id) {
                functionName = (0, utils_1.getVariableDeclaratorId)(path, j)?.name;
            }
            // target properties mapping, only contains `params` and `searchParams`
            const propertiesMap = new Map();
            let allProperties = [];
            const isRoute = !isDefaultExport && utils_1.TARGET_ROUTE_EXPORTS.has(functionName);
            // generateMetadata API has 2 params
            if (functionName === 'generateMetadata') {
                if (params.length > 2 || params.length === 0)
                    return;
            }
            else if (isRoute) {
                if (params.length !== 2)
                    return;
            }
            else {
                // Page/Layout default export have 1 param
                if (params.length !== 1)
                    return;
            }
            const propsIdentifier = (0, utils_1.generateUniqueIdentifier)(PAGE_PROPS, path, j);
            const propsArgumentIndex = isRoute ? 1 : 0;
            const currentParam = params[propsArgumentIndex];
            if (!currentParam)
                return;
            // Argument destructuring case
            if (currentParam.type === 'ObjectPattern') {
                // Validate if the properties are not `params` and `searchParams`,
                // if they are, quit the transformation
                let foundTargetProp = false;
                for (const prop of currentParam.properties) {
                    if ('key' in prop && prop.key.type === 'Identifier') {
                        const propName = prop.key.name;
                        if (utils_1.TARGET_PROP_NAMES.has(propName)) {
                            foundTargetProp = true;
                        }
                    }
                }
                // If there's no `params` or `searchParams` matched, return
                if (!foundTargetProp)
                    return;
                allProperties = currentParam.properties;
                currentParam.properties.forEach((prop) => {
                    if (
                    // Could be `Property` or `ObjectProperty`
                    (j.Property.check(prop) || j.ObjectProperty.check(prop)) &&
                        j.Identifier.check(prop.key) &&
                        utils_1.TARGET_PROP_NAMES.has(prop.key.name)) {
                        const value = 'value' in prop ? prop.value : null;
                        propertiesMap.set(prop.key.name, value);
                    }
                });
                modifiedPropArgument = true;
            }
            else if (currentParam.type === 'Identifier') {
                // case of accessing the props.params.<name>:
                // Page(props) {}
                // generateMetadata(props, parent?) {}
                const argName = currentParam.name;
                if (isClientComponent) {
                    const modifiedProp = applyUseAndRenameAccessedProp(argName, path, j);
                    if (modifiedProp) {
                        needsReactUseImport = true;
                        modified = true;
                    }
                }
                else {
                    // If it's (props.params).<name>, await the member access
                    // const pathOfCurrentParam = path.get('params', propsArgumentIndex)
                    // const paramScope = findClosetParentFunctionScope(pathOfCurrentParam, j)
                    const awaited = awaitMemberAccessOfProp(argName, path, j);
                    modified ||= awaited;
                }
                modified ||= modifyTypes(currentParam.typeAnnotation, propsIdentifier, root, j);
                // cases of passing down `props` into any function
                // Page(props) { callback(props) }
                // search for all the argument of CallExpression, where currentParam is one of the arguments
                const callExpressions = j(path).find(j.CallExpression, {
                    arguments: (args) => {
                        return args.some((arg) => {
                            return (j.Identifier.check(arg) &&
                                arg.name === argName &&
                                arg.type === 'Identifier');
                        });
                    },
                });
                // Add a comment to warn users that properties of `props` need to be awaited when accessed
                callExpressions.forEach((callExpression) => {
                    // find the argument `currentParam`
                    const args = callExpression.value.arguments;
                    const propPassedAsArg = args.find((arg) => j.Identifier.check(arg) && arg.name === argName);
                    const comment = ` ${utils_1.NEXT_CODEMOD_ERROR_PREFIX} '${argName}' is passed as an argument. Any asynchronous properties of 'props' must be awaited when accessed. `;
                    const inserted = (0, utils_1.insertCommentOnce)(propPassedAsArg, j, comment);
                    modified ||= inserted;
                });
                if (modified) {
                    modifyTypes(currentParam.typeAnnotation, propsIdentifier, root, j);
                }
            }
            if (modifiedPropArgument) {
                const isModified = resolveAsyncProp(path, propertiesMap, propsIdentifier.name, allProperties, isDefaultExport);
                if (isModified) {
                    // Make TS happy
                    if (j.ObjectPattern.check(currentParam)) {
                        modifyTypes(currentParam.typeAnnotation, propsIdentifier, root, j);
                    }
                    // Override the first param to `props`
                    params[propsArgumentIndex] = propsIdentifier;
                    modified = true;
                }
            }
            else {
                // When the prop argument is not destructured, we need to add comments to the spread properties
                if (j.Identifier.check(currentParam)) {
                    const commented = commentSpreadProps(path, currentParam.name, j);
                    const modifiedTypes = modifyTypes(currentParam.typeAnnotation, propsIdentifier, root, j);
                    modified ||= commented || modifiedTypes;
                }
            }
        }
        // Helper function to insert `const params = await asyncParams;` at the beginning of the function body
        function resolveAsyncProp(path, propertiesMap, propsIdentifierName, allProperties, isDefaultExport) {
            // Rename props to `prop` argument for the function
            const insertedRenamedPropFunctionNames = new Set();
            const node = path.value;
            // If it's sync default export, and it's also server component, make the function async
            if (isDefaultExport && !isClientComponent) {
                const hasReactHooksUsage = (0, utils_1.containsReactHooksCallExpressions)(path.get('body'), j);
                if (node.async === false && !hasReactHooksUsage) {
                    node.async = true;
                    (0, utils_1.turnFunctionReturnTypeToAsync)(node, j);
                }
            }
            // If it's arrow function and function body is not block statement, check if the properties are used there
            if (j.ArrowFunctionExpression.check(path.node) &&
                !j.BlockStatement.check(path.node.body)) {
                const objectExpression = path.node.body;
                let hasUsedProps = false;
                j(objectExpression)
                    .find(j.Identifier)
                    .forEach((identifierPath) => {
                    const idName = identifierPath.value.name;
                    if (propertiesMap.has(idName)) {
                        hasUsedProps = true;
                        return;
                    }
                });
                // Turn the function body to block statement, return the object expression
                if (hasUsedProps) {
                    path.node.body = j.blockStatement([
                        j.returnStatement(objectExpression),
                    ]);
                }
            }
            const isAsyncFunc = !!node.async;
            const functionName = path.value.id?.name || 'default';
            const functionBody = (0, utils_1.findFunctionBody)(path);
            const functionBodyPath = path.get('body');
            const hasReactHooksUsage = (0, utils_1.containsReactHooksCallExpressions)(functionBodyPath, j);
            const hasOtherProperties = allProperties.length > propertiesMap.size;
            function createDestructuringDeclaration(properties, destructPropsIdentifierName) {
                const propsToKeep = [];
                let restProperty = null;
                // Iterate over the destructured properties
                properties.forEach((property) => {
                    if (j.ObjectProperty.check(property)) {
                        // Handle normal and computed properties
                        const keyName = j.Identifier.check(property.key)
                            ? property.key.name
                            : j.Literal.check(property.key)
                                ? property.key.value
                                : null; // for computed properties
                        if (typeof keyName === 'string') {
                            propsToKeep.push(property);
                        }
                    }
                    else if (j.RestElement.check(property)) {
                        restProperty = property;
                    }
                });
                if (propsToKeep.length === 0 && !restProperty) {
                    return null;
                }
                if (restProperty) {
                    propsToKeep.push(restProperty);
                }
                return j.variableDeclaration('const', [
                    j.variableDeclarator(j.objectPattern(propsToKeep), j.identifier(destructPropsIdentifierName)),
                ]);
            }
            if (hasOtherProperties) {
                /**
                 * If there are other properties, we need to keep the original param with destructuring
                 * e.g.
                 * input:
                 * Page({ params: { slug }, otherProp }) {
                 *   const { slug } = await props.params;
                 * }
                 *
                 * output:
                 * Page(props) {
                 *   const { otherProp } = props; // inserted
                 *   // ...rest of the function body
                 * }
                 */
                const restProperties = allProperties.filter((prop) => {
                    const isTargetProps = 'key' in prop &&
                        prop.key.type === 'Identifier' &&
                        utils_1.TARGET_PROP_NAMES.has(prop.key.name);
                    return !isTargetProps;
                });
                const destructionOtherPropertiesDeclaration = createDestructuringDeclaration(restProperties, propsIdentifierName);
                if (functionBody && destructionOtherPropertiesDeclaration) {
                    functionBody.unshift(destructionOtherPropertiesDeclaration);
                }
            }
            let modifiedPropertyCount = 0;
            for (const [matchedPropName, paramsProperty] of propertiesMap) {
                if (!utils_1.TARGET_PROP_NAMES.has(matchedPropName)) {
                    continue;
                }
                // In client component, if the param is already wrapped with `use()`, skip the transformation
                if (isClientComponent) {
                    let shouldSkip = false;
                    const propPaths = j(path).find(j.Identifier, {
                        name: matchedPropName,
                    });
                    for (const propPath of propPaths.paths()) {
                        if ((0, utils_1.isParentUseCallExpression)(propPath, j)) {
                            // Skip transformation
                            shouldSkip = true;
                            break;
                        }
                    }
                    if (shouldSkip) {
                        continue;
                    }
                }
                const paramsPropertyName = j.Identifier.check(paramsProperty)
                    ? paramsProperty.name
                    : null;
                const paramPropertyName = paramsPropertyName || matchedPropName;
                // If propName is an identifier and not used in lower scope,
                // also skip the transformation.
                const hasUsedInBody = j(functionBodyPath)
                    .find(j.Identifier, {
                    name: paramPropertyName,
                })
                    .size() > 0;
                if (!hasUsedInBody && j.Identifier.check(paramsProperty))
                    continue;
                // Search the usage of propName in the function body,
                // if they're all awaited or wrapped with use(), skip the transformation
                const propUsages = j(functionBodyPath).find(j.Identifier, {
                    name: paramPropertyName,
                });
                // if there's usage of the propName, then do the check
                if (propUsages.size()) {
                    let hasMissingAwaited = false;
                    propUsages.forEach((propUsage) => {
                        // If the parent is not AwaitExpression, it's not awaited
                        const isAwaited = propUsage.parentPath?.value.type === 'AwaitExpression';
                        const isAwaitedByUse = (0, utils_1.isParentUseCallExpression)(propUsage, j);
                        if (!isAwaited && !isAwaitedByUse) {
                            hasMissingAwaited = true;
                            return;
                        }
                    });
                    // If all the usages of parm are awaited, skip the transformation
                    if (!hasMissingAwaited) {
                        continue;
                    }
                }
                modifiedPropertyCount++;
                const propNameIdentifier = j.identifier(matchedPropName);
                const propsIdentifier = j.identifier(propsIdentifierName);
                const accessedPropIdExpr = j.memberExpression(propsIdentifier, propNameIdentifier);
                // Check param property value, if it's destructed, we need to destruct it as well
                // e.g.
                // input: Page({ params: { slug } })
                // output: const { slug } = await props.params; rather than const props = await props.params;
                const uid = functionName + ':' + paramPropertyName;
                if (paramsProperty?.type === 'ObjectPattern') {
                    const objectPattern = paramsProperty;
                    const objectPatternProperties = objectPattern.properties;
                    // destruct the object pattern, e.g. { slug } => const { slug } = params;
                    const destructedObjectPattern = j.variableDeclaration('const', [
                        j.variableDeclarator(j.objectPattern(objectPatternProperties.map((prop) => {
                            if (prop.type === 'Property' &&
                                prop.key.type === 'Identifier') {
                                return j.objectProperty(j.identifier(prop.key.name), j.identifier(prop.key.name));
                            }
                            return prop;
                        })), propNameIdentifier),
                    ]);
                    if (!insertedDestructPropNames.has(uid) && functionBody) {
                        functionBody.unshift(destructedObjectPattern);
                        insertedDestructPropNames.add(uid);
                    }
                }
                if (isAsyncFunc) {
                    // If it's async function, add await to the async props.<propName>
                    const paramAssignment = j.variableDeclaration('const', [
                        j.variableDeclarator(j.identifier(paramPropertyName), j.awaitExpression(accessedPropIdExpr)),
                    ]);
                    if (!insertedRenamedPropFunctionNames.has(uid) && functionBody) {
                        functionBody.unshift(paramAssignment);
                        insertedRenamedPropFunctionNames.add(uid);
                    }
                }
                else {
                    if (!isClientComponent &&
                        (0, utils_1.isFunctionType)(node.type) &&
                        !hasReactHooksUsage) {
                        // If it's export function, populate the function to async
                        node.async = true;
                        (0, utils_1.turnFunctionReturnTypeToAsync)(node, j);
                        // Insert `const <propName> = await props.<propName>;` at the beginning of the function body
                        const paramAssignment = j.variableDeclaration('const', [
                            j.variableDeclarator(j.identifier(paramPropertyName), j.awaitExpression(accessedPropIdExpr)),
                        ]);
                        if (!insertedRenamedPropFunctionNames.has(uid) && functionBody) {
                            functionBody.unshift(paramAssignment);
                            insertedRenamedPropFunctionNames.add(uid);
                        }
                    }
                    else {
                        const paramAssignment = j.variableDeclaration('const', [
                            j.variableDeclarator(j.identifier(paramPropertyName), j.callExpression(j.identifier('use'), [accessedPropIdExpr])),
                        ]);
                        if (!insertedRenamedPropFunctionNames.has(uid) && functionBody) {
                            needsReactUseImport = true;
                            functionBody.unshift(paramAssignment);
                            insertedRenamedPropFunctionNames.add(uid);
                        }
                    }
                }
            }
            return modifiedPropertyCount > 0;
        }
        const defaultExportsDeclarations = root.find(j.ExportDefaultDeclaration);
        defaultExportsDeclarations.forEach((path) => {
            const functionPath = (0, utils_1.getFunctionPathFromExportPath)(path, j, root, () => true);
            if (functionPath) {
                renameAsyncPropIfExisted(functionPath, true);
            }
        });
        // Matching Next.js functional named export of route entry:
        // - export function <named>(...) { ... }
        // - export const <named> = ...
        const namedExportDeclarations = root.find(j.ExportNamedDeclaration);
        namedExportDeclarations.forEach((path) => {
            const functionPath = (0, utils_1.getFunctionPathFromExportPath)(path, j, root, (idName) => utils_1.TARGET_NAMED_EXPORTS.has(idName));
            if (functionPath) {
                renameAsyncPropIfExisted(functionPath, false);
            }
        });
    }
    const isClientComponent = (0, utils_1.determineClientDirective)(root, j);
    // Apply to `params` and `searchParams`
    processAsyncPropOfEntryFile(isClientComponent);
    // Add import { use } from 'react' if needed and not already imported
    if (needsReactUseImport) {
        (0, utils_1.insertReactUseImport)(root, j);
    }
    const commented = commentOnMatchedReExports(root, j);
    modified ||= commented;
    return modified ? root.toSource() : null;
}
function findAllTypes(root, j, typeName) {
    const types = {
        interfaces: [],
        typeAliases: [],
        imports: [],
        references: [],
    };
    // Step 1: Find all interface declarations with the specified name
    root
        .find(j.TSInterfaceDeclaration, {
        id: {
            type: 'Identifier',
            name: typeName,
        },
    })
        .forEach((path) => {
        types.interfaces.push(path.node);
    });
    // Step 2: Find all type alias declarations with the specified name
    root
        .find(j.TSTypeAliasDeclaration, {
        id: {
            type: 'Identifier',
            name: typeName,
        },
    })
        .forEach((path) => {
        types.typeAliases.push(path.node);
    });
    // Step 3: Find all imported types with the specified name
    root
        .find(j.ImportSpecifier, {
        imported: {
            type: 'Identifier',
            name: typeName,
        },
    })
        .forEach((path) => {
        types.imports.push(path.node);
    });
    // Step 4: Find all references to the specified type
    root
        .find(j.TSTypeReference, {
        typeName: {
            type: 'Identifier',
            name: typeName,
        },
    })
        .forEach((path) => {
        types.references.push(path.node);
    });
    return types;
}
function commentSpreadProps(path, propsIdentifierName, j) {
    let modified = false;
    const functionBody = (0, utils_1.findFunctionBody)(path);
    const functionBodyCollection = j(functionBody);
    // Find all the usage of spreading properties of `props`
    const jsxSpreadProperties = functionBodyCollection.find(j.JSXSpreadAttribute, { argument: { name: propsIdentifierName } });
    const objSpreadProperties = functionBodyCollection.find(j.SpreadElement, {
        argument: { name: propsIdentifierName },
    });
    const comment = ` ${utils_1.NEXT_CODEMOD_ERROR_PREFIX} '${propsIdentifierName}' is used with spread syntax (...). Any asynchronous properties of '${propsIdentifierName}' must be awaited when accessed. `;
    // Add comment before it
    jsxSpreadProperties.forEach((spread) => {
        const inserted = (0, utils_1.insertCommentOnce)(spread.value, j, comment);
        if (inserted)
            modified = true;
    });
    objSpreadProperties.forEach((spread) => {
        const inserted = (0, utils_1.insertCommentOnce)(spread.value, j, comment);
        if (inserted)
            modified = true;
    });
    return modified;
}
//# sourceMappingURL=next-async-dynamic-prop.js.map