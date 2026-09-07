"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.install = install;
/* eslint-disable import/no-extraneous-dependencies */
const picocolors_1 = require("picocolors");
const cross_spawn_1 = __importDefault(require("cross-spawn"));
/**
 * Spawn a package manager installation with either Yarn or NPM.
 *
 * @returns A Promise that resolves once the installation is finished.
 */
function install(root, dependencies, { useYarn, isOnline, devDependencies }) {
    /**
     * NPM-specific command-line flags.
     */
    const npmFlags = ['--logLevel', 'error'];
    /**
     * Yarn-specific command-line flags.
     */
    const yarnFlags = [];
    /**
     * Return a Promise that resolves once the installation is finished.
     */
    return new Promise((resolve, reject) => {
        let args;
        let command = useYarn ? 'yarnpkg' : 'npm';
        if (dependencies && dependencies.length) {
            /**
             * If there are dependencies, run a variation of `{displayCommand} add`.
             */
            if (useYarn) {
                /**
                 * Call `yarn add --exact (--offline)? (-D)? ...`.
                 */
                args = ['add', '--exact'];
                if (!isOnline)
                    args.push('--offline');
                args.push('--cwd', root);
                if (devDependencies)
                    args.push('--dev');
                args.push(...dependencies);
            }
            else {
                /**
                 * Call `npm install [--save|--save-dev] ...`.
                 */
                args = ['install', '--save-exact'];
                args.push(devDependencies ? '--save-dev' : '--save');
                args.push(...dependencies);
            }
        }
        else {
            /**
             * If there are no dependencies, run a variation of `{displayCommand}
             * install`.
             */
            args = ['install'];
            if (!isOnline) {
                console.log((0, picocolors_1.yellow)('You appear to be offline.'));
                if (useYarn) {
                    console.log((0, picocolors_1.yellow)('Falling back to the local Yarn cache.'));
                    console.log();
                    args.push('--offline');
                }
                else {
                    console.log();
                }
            }
        }
        /**
         * Add any package manager-specific flags.
         */
        if (useYarn) {
            args.push(...yarnFlags);
        }
        else {
            args.push(...npmFlags);
        }
        /**
         * Spawn the installation process.
         */
        const child = (0, cross_spawn_1.default)(command, args, {
            stdio: 'inherit',
            env: { ...process.env, ADBLOCK: '1', DISABLE_OPENCOLLECTIVE: '1' },
        });
        child.on('close', (code) => {
            if (code !== 0) {
                reject({ command: `${command} ${args.join(' ')}` });
                return;
            }
            resolve();
        });
    });
}
//# sourceMappingURL=install.js.map