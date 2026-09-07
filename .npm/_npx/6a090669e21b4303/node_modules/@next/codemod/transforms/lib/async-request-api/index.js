"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = transform;
const next_async_dynamic_prop_1 = require("./next-async-dynamic-prop");
const next_async_dynamic_api_1 = require("./next-async-dynamic-api");
function transform(file, api) {
    const transforms = [next_async_dynamic_prop_1.transformDynamicProps, next_async_dynamic_api_1.transformDynamicAPI];
    return transforms.reduce((source, transformFn) => {
        const result = transformFn(source, api, file.path);
        if (!result) {
            return source;
        }
        return result;
    }, file.source);
}
//# sourceMappingURL=index.js.map