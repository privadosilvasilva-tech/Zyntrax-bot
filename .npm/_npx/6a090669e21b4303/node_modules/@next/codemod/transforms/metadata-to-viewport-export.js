"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = transformer;
const parser_1 = require("../lib/parser");
function transformer(file, _api) {
    const j = (0, parser_1.createParserFromPath)(file.path);
    const root = j(file.source);
    // Find the metadata export
    const metadataExport = root.find(j.ExportNamedDeclaration, {
        declaration: {
            type: 'VariableDeclaration',
            declarations: [
                {
                    id: { name: 'metadata' },
                },
            ],
        },
    });
    if (metadataExport.size() !== 1) {
        return file.source;
    }
    const metadataObject = metadataExport.find(j.ObjectExpression).get(0).node;
    if (!metadataObject) {
        console.error('Could not find metadata object');
        return file.source;
    }
    let metadataProperties = metadataObject.properties;
    let viewportProperties;
    let hasChanges = false;
    const viewport = metadataProperties.find((prop) => prop.key.name === 'viewport');
    if (viewport) {
        viewportProperties = viewport.value.properties;
        metadataProperties = metadataProperties.filter((prop) => prop.key.name !== 'viewport');
        hasChanges = true;
    }
    else {
        viewportProperties = [];
    }
    const colorScheme = metadataProperties.find((prop) => prop.key.name === 'colorScheme');
    if (colorScheme) {
        viewportProperties.push(colorScheme);
        metadataProperties = metadataProperties.filter((prop) => prop.key.name !== 'colorScheme');
        hasChanges = true;
    }
    const themeColor = metadataProperties.find((prop) => prop.key.name === 'themeColor');
    if (themeColor) {
        viewportProperties.push(themeColor);
        metadataProperties = metadataProperties.filter((prop) => prop.key.name !== 'themeColor');
        hasChanges = true;
    }
    // Only apply changes if there were actual modifications
    if (!hasChanges) {
        return file.source;
    }
    // Update the metadata export
    metadataExport
        .find(j.ObjectExpression)
        .replaceWith(j.objectExpression(metadataProperties));
    // Create the new viewport object
    const viewportExport = j.exportNamedDeclaration(j.variableDeclaration('const', [
        j.variableDeclarator(j.identifier('viewport'), j.objectExpression(viewportProperties)),
    ]));
    // Append the viewport export to the body of the program
    if (viewportProperties.length) {
        root.get().node.program.body.push(viewportExport);
    }
    return root.toSource();
}
//# sourceMappingURL=metadata-to-viewport-export.js.map