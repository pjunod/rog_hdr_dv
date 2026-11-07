// SPDX-License-Identifier: GPL-2.0-only
// Offline definitions. Execute only after independent source review/fixes.
// Loads actual patched extension classes and exact extracted Shell methods.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

import vm from 'node:vm';

const [source, shellFile, ...selectedNames] = process.argv.slice(2);
assert(source && shellFile, 'usage: node tests/tiling-animation-ownership.mjs EXTENSION_ROOT SHELL_WINDOW_MANAGER_JS [EXACT_CASE_NAME ...]');
const registry = JSON.parse(readFileSync(new URL('../sources.json', import.meta.url), 'utf8'));
const pin = registry.series.find(item => item.component === 'ubuntu-tiling-assistant');
assert.equal(execFileSync('git', ['rev-parse', 'HEAD^{tree}'], { cwd: source, encoding: 'utf8' }).trim(), pin.candidate_tree);
assert.equal(execFileSync('git', ['status', '--porcelain', '--untracked-files=no'], { cwd: source, encoding: 'utf8' }).trim(), '');
const shellText = readFileSync(shellFile, 'utf8');
assert.equal(createHash('sha256').update(shellText).digest('hex'),
    'b7a7e6ea249f77496f5b84f76d1b3ee7f14f2c3d659392513998b3c46827ae47');
// The sibling resource is required: the actual ease wrapper is part of the API.
const environmentText = readFileSync(resolve(shellFile, '..', 'environment.js'), 'utf8');
assert.equal(createHash('sha256').update(environmentText).digest('hex'),
    pin.shell_api_reference.environment_js_sha256);
const easeWrapper = environmentText.match(
    /^Clutter\.Actor\.prototype\.ease = function \(props\) \{[^]*?^\};/m)?.[0];
assert(easeWrapper, 'missing actual Shell callback ease wrapper');
const read = name => readFileSync(resolve(source, 'src/extension', name), 'utf8');
const withoutImports = text => text.replace(/^import .*;\n/gm, '')
    .replace(/^export default /gm, '').replace(/^export /gm, '');
const shellMethods = ['_sizeChangeWindow', '_prepareAnimationInfo', '_sizeChangedWindow',
    '_clearAnimationInfo', '_sizeChangeWindowDone'].map(name => {
    const match = shellText.match(new RegExp(`^    ${name}\\([^]*?^    }`, 'm'));
    assert(match, `missing actual Shell method ${name}`);
    return match[0];
}).join('\n');

class Signals {
    next = 1;
    handlers = new Map();
    connect(name, fn) { const id = this.next++; this.handlers.set(id, { name, fn }); return id; }
    disconnect(id) { assert(this.handlers.delete(id), `unknown signal ${id}`); }
    emit(name, ...args) {
        for (const [id, item] of [...this.handlers])
            if (item.name === name && this.handlers.has(id)) item.fn(this, ...args);
    }
    connectObject(name, fn, owner) {
        const id = this.connect(name, fn);
        owner.connect('destroy', () => { if (this.handlers.has(id)) this.disconnect(id); });
    }
}

function environment({ synchronous = false, reduced = false } = {}) {
    const laters = new Map();
    const errors = [];
    let nextLater = 1;
    const clones = [];
    const captures = [];
    class Actor extends Signals {
        scale_x = 1; scale_y = 1; translation_x = 0; translation_y = 0;
        opacity = 255; frozen = 0; freezes = 0; thaws = 0;
        transitions = new Map();
        constructor(props = {}) { super(); Object.assign(this, props); }
        paint_to_content(rect) {
            const content = { rect: { ...rect }, scale_x: this.scale_x, scale_y: this.scale_y,
                translation_x: this.translation_x, translation_y: this.translation_y,
                opacity: this.opacity, frozen: this.frozen };
            captures.push(content);
            return content;
        }
        set_offscreen_redirect() {}
        set_position(x, y) { Object.assign(this, { x, y }); }
        set_size(width, height) { Object.assign(this, { width, height }); }
        freeze() { this.frozen++; this.freezes++; }
        thaw() { assert(this.frozen > 0, 'unbalanced thaw'); this.frozen--; this.thaws++; }
        get_transition(name) { return this.transitions.get(name) ?? null; }
        remove_transition(name) {
            const transition = this.transitions.get(name);
            this.transitions.delete(name);
            if (transition) transition.stop?.();
        }
        remove_all_transitions() {
            for (const name of [...this.transitions.keys()]) this.remove_transition(name);
        }
        easeImpl(props) {
            this.lastEase = props;
            this.lastStopped = props.onStopped;
            const keys = Object.keys(props).filter(key =>
                !['duration', 'mode', 'onStopped', 'onComplete'].includes(key));
            let resolveEase, rejectEase;
            const promise = new Promise((resolve, reject) => {
                resolveEase = resolve; rejectEase = reject;
            });
            let stopped = false;
            const stop = (finished = false) => {
                if (stopped) return;
                stopped = true;
                props.onStopped?.(finished);
                if (finished) resolveEase();
                else rejectEase({ matches: (_domain, code) => code === 1 });
            };
            for (const key of keys) {
                const name = key.replaceAll('_', '-');
                this.remove_transition(name);
                this.transitions.set(name, { stop, key, target: props[key] });
            }
            this.finish = () => {
                for (const key of keys) {
                    this.transitions.delete(key.replaceAll('_', '-'));
                    this[key] = props[key];
                }
                stop(true); props.onComplete?.();
            };
            if (synchronous) this.finish();
            return promise;
        }
        destroy() {
            if (this.destroyed) return;
            this.destroyed = true; this.emit('destroy'); this.remove_all_transitions();
        }
    }
    class Widget extends Actor {
        constructor(props) { super(props); clones.push(this); }
    }
    const wm = new Signals();
    wm.completions = 0; wm.nativeCount = 0;
    wm.completed_size_change = () => { wm.completions++; assert(--wm.nativeCount >= 0); };
    const latersApi = {
        add(_type, callback) { const id = nextLater++; laters.set(id, callback); return id; },
        remove(id) { laters.delete(id); }
    };
    const workArea = { x: 0, y: 0, width: 1000, height: 800 };
    const display = new Signals();
    display.get_monitor_scale = () => 1;
    const globalObject = {
        window_manager: wm, compositor: { get_laters: () => latersApi },
        display, workspace_manager: { get_active_workspace: () => ({}) }
    };
    const Main = { uiGroup: { add_child() {} }, overview: { visible: false } };
    const context = vm.createContext({
        global: globalObject, Main, log() {}, logError(error) { errors.push(error); },
        Clutter: { Actor, OffscreenRedirect: { ALWAYS: 1 }, AnimationMode: { EASE_OUT_QUAD: 1 } },
        Meta: { LaterType: { BEFORE_REDRAW: 1 }, WindowType: { NORMAL: 1 },
            MaximizeFlags: { BOTH: 3, HORIZONTAL: 1, VERTICAL: 2 } },
        St: { Widget, Settings: { get: () => ({ reducedMotion: reduced ? 1 : 0 }) },
            ReducedMotion: { REDUCE: 1 } },
        Mtk: { Rectangle: class {
            copy() { return Object.assign(new this.constructor(), this); }
            equal(other) {
                return this.x === other.x && this.y === other.y &&
                    this.width === other.width && this.height === other.height;
            }
        } },
        Settings: { getInt: () => 0, getBoolean: key => key.startsWith('enable-') },
        Gio: { _promisify() {}, File: class {}, IOErrorEnum: { CANCELLED: 1 } }, Config: { PACKAGE_VERSION: '51.0' },
        WINDOW_ANIMATION_TIME: 250
    });
    context._easeActor = (actor, props) => actor.easeImpl(props);
    context.logErrorUnlessCancelled = error => {
        if (!error?.matches?.(context.Gio.IOErrorEnum, context.Gio.IOErrorEnum.CANCELLED))
            errors.push(error);
    };
    vm.runInContext(easeWrapper, context, { filename: 'actual-environment-ease.js' });
    vm.runInContext(withoutImports(read('utility.js')), context, { filename: 'actual-utility.js' });
    vm.runInContext(withoutImports(read('windowAnimation.js')), context, { filename: 'actual-windowAnimation.js' });
    vm.runInContext(withoutImports(read('tilingWindowManager.js')), context, { filename: 'actual-tilingWindowManager.js' });
    vm.runInContext('const Twm = TilingWindowManager;', context);
    vm.runInContext(withoutImports(read('keybindingHandler.js')), context, { filename: 'actual-keybindingHandler.js' });
    const shell = vm.runInContext(`new (class {
        constructor() { this._shellwm = global.window_manager; this._resizePending = new Set(); this._resizing = new Set(); }
        _shouldAnimateActor() { return true; }
        ${shellMethods}
    })()`, context);
    Main.wm = shell;
    // Same native signal order as Shell: its listeners predate the extension.
    wm.connect('size-change', (...args) => shell._sizeChangeWindow(...args));
    wm.connect('size-changed', (...args) => shell._sizeChangedWindow(...args));
    wm.connect('kill-window-effects', (...args) => shell._sizeChangeWindowDone(...args));
    const animations = vm.runInContext('new WindowAnimations()', context);
    const Twm = vm.runInContext('TilingWindowManager', context);
    Twm._animations = animations;
    Twm.clearTilingProps = () => {};
    Twm.deleteTilingState = () => {};
    const window = new Signals();
    const actor = new Actor(); actor.meta_window = window;
    window.rect = { x: 30, y: 40, width: 300, height: 200 };
    Object.assign(window, {
        get_compositor_private: () => actor, get_frame_rect: () => ({ ...window.rect }),
        get_work_area_for_monitor: () => workArea, get_work_area_current_monitor: () => workArea,
        get_monitor: () => 0, get_id: () => 1, is_skip_taskbar: () => false,
        allows_move: () => true, allows_resize: () => true, is_fullscreen: () => false,
        unmake_fullscreen() {}, unmake_above() {}, unminimize() {}, raise_and_make_recent() {},
        move_to_monitor() {},
        move_frame(_op, x, y) { Object.assign(this.rect, { x, y }); this.emit('position-changed'); },
        move_resize_frame(_op, x, y, width, height) {
            Object.assign(this.rect, { x, y, width, height }); this.emit('position-changed'); this.emit('size-changed');
        }
    });
    globalObject.display.focus_window = window;
    const flush = () => {
        const pending = [...laters];
        for (const [id, callback] of pending) {
            if (laters.delete(id)) callback();
        }
    };
    const nativeStart = (whichChange = 1) => {
        wm.nativeCount++; wm.emit('size-change', actor, whichChange, window.get_frame_rect(), window.get_frame_rect());
    };
    const balanced = () => {
        animations.destroy();
        assert.equal(actor.frozen, 0); assert.equal(actor.freezes, actor.thaws);
        assert.equal(laters.size, 0); assert.equal(animations._effects.size, 0);
        assert.equal(window.handlers.size, 0); assert.equal(actor.handlers.size, 0);
        assert.equal(display.handlers.size, 0);
        assert.equal(errors.length, 0);
        assert(clones.every(clone => clone.destroyed));
    };
    const finishSynthetic = () => {
        const effect = animations._effects.get(actor);
        assert(effect?.started, 'expected active synthetic overlay');
        effect.clone.finish();
    };
    return { animations, actor, window, wm, shell, laters, clones, captures, display,
        flush, nativeStart, balanced, finishSynthetic, Twm, context, errors };
}

const tests = [];
const test = (name, fn) => tests.push({ name, fn });
const target = { x: 100, y: 100, width: 400, height: 300 };
function prepareAndResize(e) {
    e.animations.prepare(e.window, target);
    e.window.move_resize_frame(true, target.x, target.y, target.width, target.height);
    e.flush();
}
for (const operation of ['tile', 'untile', 'center']) {
    test(`actual ${operation} path: zero native completions and no Shell memberships`, async () => {
        const e = environment();
        if (operation === 'tile') {
            const rect = vm.runInContext('new Rect(100, 100, 400, 300)', e.context);
            await e.Twm.tile(e.window, rect, { fakeTile: true });
        } else if (operation === 'untile') {
            e.window.untiledRect = vm.runInContext('new Rect(100, 100, 400, 300)', e.context);
            e.Twm.untile(e.window);
        } else {
            await vm.runInContext('TilingKeybindingHandler.prototype._onCustomKeybindingPressed.call({}, "center-window")', e.context);
        }
        e.flush(); assert.equal(e.animations._effects.size, 1);
        e.finishSynthetic();
        assert.equal(e.wm.completions, 0);
        assert.equal(e.shell._resizePending.size, 0); assert.equal(e.shell._resizing.size, 0);
        assert.equal(e.actor.__animationInfo, undefined); e.balanced();
    });
}
for (const delayed of [false, true]) {
    test(`actual tile then default untile with real Rect: ${delayed ? 'delayed same-position size' : 'synchronous movement'}`, async () => {
        const e = environment();
        const original = e.window.get_frame_rect();
        const tiled = delayed ? 'new Rect(30, 40, 400, 300)' : 'new Rect(100, 100, 400, 300)';
        await e.Twm.tile(e.window, vm.runInContext(tiled, e.context), { fakeTile: true });
        const restored = e.window.untiledRect;
        assert.equal(vm.runInContext('Rect', e.context).prototype, Object.getPrototypeOf(restored));
        assert.deepEqual(Object.keys(restored), ['_rect'], 'exercise actual prototype getters');
        e.flush(); e.finishSynthetic();
        const beforeUntile = e.window.get_frame_rect();
        const requests = [];
        const resize = e.window.move_resize_frame;
        e.window.move_resize_frame = function (...args) {
            requests.push(args);
            if (!delayed) resize.apply(this, args);
        };
        // Use default restoreFullPos:true, passing the actual tile-created Rect.
        e.Twm.untile(e.window);
        assert.equal(requests.length, 1);
        assert.deepEqual(requests[0].slice(1), Object.values(original));
        assert.equal(e.window.untiledRect, null);
        const pending = e.animations._effects.get(e.actor);
        assert(pending, 'synchronous movement must not cancel against missing coordinates');
        assert.deepEqual({ ...pending.requestedRect }, original);
        assert.notEqual(pending.requestedRect, restored);
        // Mutate every getter-backed value after preparation but before redraw.
        restored.x = 700; restored.y = 600; restored.width = 999; restored.height = 888;
        assert.deepEqual({ ...pending.requestedRect }, original, 'independent scalar snapshot');
        e.flush();
        const effect = e.animations._effects.get(e.actor);
        assert(effect?.started, 'default untile must have actual finite overlay motion');
        assert.deepEqual({ ...effect.target }, original);
        for (const [name, expected] of Object.entries({ x: original.x, y: original.y,
            'scale-x': original.width / beforeUntile.width,
            'scale-y': original.height / beforeUntile.height, opacity: 0 })) {
            const transition = effect.clone.get_transition(name);
            assert(transition && Number.isFinite(transition.target), `finite ${name} target`);
            assert.equal(transition.target, expected);
        }
        assert.equal(effect.clone.lastEase.duration, 250);
        if (delayed) {
            assert.deepEqual(e.window.get_frame_rect(), beforeUntile);
            Object.assign(e.window.rect, original); e.window.emit('size-changed');
            assert.equal(e.animations._effects.get(e.actor), effect);
        }
        assert.equal(e.actor.transitions.size, 0); assert.equal(e.actor.freezes, 0);
        e.finishSynthetic();
        assert.equal(e.wm.completions, 0); assert.equal(e.wm.nativeCount, 0);
        assert.equal(e.shell._resizePending.size, 0); assert.equal(e.shell._resizing.size, 0);
        assert.equal(e.actor.__animationInfo, undefined); e.balanced();
    });
}
test('actual Shell native start / size-changed / completion is preserved', () => {
    const e = environment(); e.nativeStart();
    const info = e.actor.__animationInfo;
    e.animations.prepare(e.window, target);
    assert.equal(e.actor.__animationInfo, info); assert.equal(e.animations._effects.size, 0);
    e.window.move_resize_frame(true, 100, 100, 400, 300); e.wm.emit('size-changed', e.actor);
    e.animations.prepare(e.window, { ...target, x: 200 });
    assert.equal(e.actor.__animationInfo, info); assert.equal(e.animations._effects.size, 0);
    e.actor.finish(); assert.equal(e.wm.completions, 1); assert.equal(e.wm.nativeCount, 0);
    e.wm.emit('kill-window-effects', e.actor); assert.equal(e.wm.completions, 1); e.balanced();
});
test('actual Shell pending native cancellation completes exactly once', () => {
    const e = environment(); e.nativeStart();
    e.wm.emit('kill-window-effects', e.actor);
    assert.equal(e.wm.completions, 1); assert.equal(e.wm.nativeCount, 0);
    e.wm.emit('size-changed', e.actor);
    assert.equal(e.wm.completions, 1); e.balanced();
});
test('native resize cancels synthetic pending or active records, then completes once', () => {
    for (const active of [false, true]) {
        const e = environment();
        if (active) prepareAndResize(e); else e.animations.prepare(e.window, target);
        e.nativeStart(); assert.equal(e.animations._effects.size, 0);
        e.window.move_resize_frame(true, 200, 200, 600, 400); e.wm.emit('size-changed', e.actor);
        e.actor.finish(); assert.equal(e.wm.completions, 1); e.balanced();
    }
});
for (const change of ['MAXIMIZE', 'FULLSCREEN']) {
    test(`Shell-first native ${change} capture sees pristine live actor during synthetic effect`, () => {
        const e = environment(); prepareAndResize(e);
        assert.equal(e.actor.transitions.size, 0); assert.equal(e.actor.freezes, 0);
        const overlay = e.animations._effects.get(e.actor).clone;
        assert(overlay.get_transition('scale-x'), 'motion still exists on overlay');
        e.nativeStart(change);
        const capture = e.captures.at(-1);
        assert.deepEqual(capture, { rect: e.window.get_frame_rect(), scale_x: 1, scale_y: 1,
            translation_x: 0, translation_y: 0, opacity: 255, frozen: 0 });
        assert.equal(e.actor.__animationInfo.clone.content, capture); assert(overlay.destroyed);
        e.window.move_resize_frame(true, 0, 0, 1000, 800); e.wm.emit('size-changed', e.actor);
        e.actor.finish(); assert.equal(e.wm.completions, 1); e.balanced();
    });
}
test('rapid overlapping preparation and stale stopped callbacks cannot clear a new record', () => {
    const e = environment(); prepareAndResize(e);
    const stale = e.animations._effects.get(e.actor).clone.lastStopped;
    e.animations.prepare(e.window, { ...target, x: 200 });
    const current = e.animations._effects.get(e.actor); stale();
    assert.equal(e.animations._effects.get(e.actor), current);
    e.window.move_frame(false, 200, 100); e.flush(); e.finishSynthetic();
    assert.equal(e.wm.completions, 0); e.balanced();
});
test('actual rapid retile skips redundant animation but cancels previous effect', async () => {
    const e = environment();
    await e.Twm.tile(e.window, vm.runInContext('new Rect(100, 100, 400, 300)', e.context), { fakeTile: true });
    e.flush();
    await e.Twm.tile(e.window, vm.runInContext('new Rect(200, 100, 400, 300)', e.context), { fakeTile: true });
    assert.equal(e.animations._effects.size, 0); assert.equal(e.wm.completions, 0); e.balanced();
});
test('kill / minimize / map / unmanage / actor destruction clean pending and active effects', () => {
    for (const signal of ['kill-window-effects', 'minimize', 'map', 'destroy', 'unmanaging', 'actor-destroy']) {
        for (const active of [false, true]) {
            const e = environment();
            if (active) prepareAndResize(e); else e.animations.prepare(e.window, target);
            if (signal === 'actor-destroy') e.actor.destroy();
            else if (signal === 'unmanaging') e.window.emit(signal);
            else e.wm.emit(signal, e.actor);
            e.flush(); assert.equal(e.animations._effects.size, 0);
            assert.equal(e.wm.completions, 0); e.balanced();
        }
    }
});
for (const operation of ['tile', 'untile']) {
    for (const outcome of ['matching', 'constrained', 'refused', 'after-completion']) {
        test(`actual delayed size-only ${operation}: finite motion with ${outcome} geometry`, async () => {
            const e = environment();
            const old = e.window.get_frame_rect();
            const requested = { ...old, width: 400, height: 300 };
            const requests = [];
            // The actual callers issue requests, but the client has not committed.
            e.window.move_resize_frame = (...args) => requests.push(args);
            if (operation === 'tile') {
                await e.Twm.tile(e.window, vm.runInContext('new Rect(30, 40, 400, 300)', e.context), { fakeTile: true });
            } else {
                e.window.isTiled = true;
                e.window.untiledRect = { x: 900, y: 700, width: 400, height: 300 };
                e.Twm.untile(e.window, { restoreFullPos: false });
            }
            assert.equal(requests.length, 1);
            assert.deepEqual(requests[0].slice(1), Object.values(requested));
            assert.deepEqual(e.window.get_frame_rect(), old);
            e.flush();
            const effect = e.animations._effects.get(e.actor);
            assert(effect?.started, 'delayed size-only operation must actually animate');
            assert.deepEqual({ ...effect.target }, requested);
            assert.equal(effect.clone.get_transition('scale-x').target, 400 / old.width);
            assert.equal(effect.clone.get_transition('scale-y').target, 300 / old.height);
            assert.equal(effect.clone.get_transition('opacity').target, 0);
            assert.equal(effect.clone.lastEase.duration, 250, 'finite transition, not reply waiting');
            assert.equal(e.actor.transitions.size, 0); assert.equal(e.actor.freezes, 0);
            // Duplicate old-frame notifications are not a changed actual frame.
            e.window.emit('position-changed'); e.window.emit('size-changed');
            assert.equal(e.animations._effects.get(e.actor), effect);
            if (outcome === 'matching' || outcome === 'constrained') {
                Object.assign(e.window.rect, requested,
                    outcome === 'constrained' ? { width: 396, height: 288 } : {});
                e.window.emit('size-changed');
                if (outcome === 'matching') {
                    assert.equal(e.animations._effects.get(e.actor), effect);
                    e.window.emit('position-changed'); e.window.emit('size-changed');
                    assert.equal(e.animations._effects.get(e.actor), effect);
                    e.finishSynthetic();
                } else {
                    assert.equal(e.animations._effects.size, 0); assert(effect.clone.destroyed);
                }
            } else {
                // Refusal expires through the animation's own stopped callback.
                e.finishSynthetic(); assert(effect.clone.destroyed);
                assert.equal(e.animations._effects.size, 0);
                if (outcome === 'after-completion') Object.assign(e.window.rect, requested);
                else e.window.rect.width = 320; // unrelated later programmatic resize
                e.window.emit('size-changed'); e.flush();
                assert.equal(e.animations._effects.size, 0);
            }
            assert.equal(e.wm.completions, 0); e.balanced();
        });
    }
}
test('provisional visual destination copies requested geometry and keeps finite motion', () => {
    const e = environment(); const requested = { ...target };
    e.animations.prepare(e.window, requested); requested.width = 999;
    e.flush(); const effect = e.animations._effects.get(e.actor);
    assert.deepEqual({ ...effect.target }, target);
    assert.equal(effect.clone.get_transition('x').target, target.x);
    assert.equal(effect.clone.get_transition('y').target, target.y);
    assert.equal(effect.clone.get_transition('scale-x').target, target.width / 300);
    e.finishSynthetic(); assert.equal(e.wm.completions, 0); e.balanced();
});
test('active provisional A superseded by B cannot survive differing late A geometry', () => {
    const e = environment(); e.animations.prepare(e.window, target); e.flush();
    const a = e.animations._effects.get(e.actor);
    const bTarget = { ...target, width: 500 };
    e.animations.prepare(e.window, bTarget); e.flush();
    const b = e.animations._effects.get(e.actor);
    assert(a.clone.destroyed); assert(b.started);
    assert.equal(b.clone.get_transition('scale-x').target, 500 / 300);
    a.clone.lastStopped(); assert.equal(e.animations._effects.get(e.actor), b);
    Object.assign(e.window.rect, target); e.window.emit('size-changed');
    assert.equal(e.animations._effects.size, 0); assert(b.clone.destroyed);
    Object.assign(e.window.rect, bTarget); e.window.emit('size-changed'); e.flush();
    assert.equal(e.animations._effects.size, 0); assert.equal(e.wm.completions, 0); e.balanced();
});
test('async A/B supersession never binds B snapshot to A or retains stale geometry', () => {
    for (const aBeforeRedraw of [false, true]) {
        const e = environment();
        e.animations.prepare(e.window, target);
        e.animations.prepare(e.window, { ...target, x: 200, width: 500 });
        assert.equal(e.animations._effects.size, 0);
        if (aBeforeRedraw) e.window.move_resize_frame(true, 100, 100, 400, 300);
        e.flush();
        if (!aBeforeRedraw) e.window.move_resize_frame(true, 100, 100, 400, 300);
        e.window.move_resize_frame(true, 200, 100, 500, 300); e.flush();
        assert.equal(e.animations._effects.size, 0); assert.equal(e.wm.completions, 0); e.balanced();
    }
});
test('actual tile to untile before async A/B replies does not prepare an ambiguous B', async () => {
    const e = environment(); const requests = [];
    e.window.move_frame = () => {};
    e.window.move_resize_frame = (...args) => requests.push(args);
    await e.Twm.tile(e.window, vm.runInContext('new Rect(100, 100, 400, 300)', e.context), { fakeTile: true });
    e.Twm.untile(e.window);
    assert.equal(requests.length, 2); assert.equal(e.animations._effects.size, 0);
    for (const [, x, y, width, height] of requests) {
        Object.assign(e.window.rect, { x, y, width, height });
        e.window.emit('position-changed'); e.window.emit('size-changed'); e.flush();
        assert.equal(e.animations._effects.size, 0);
    }
    assert.equal(e.wm.completions, 0); e.balanced();
});
test('active geometry revisions cancel overlays, including late size after position-only motion', () => {
    for (const change of ['move', 'size', 'late-size']) {
        const e = environment();
        if (change === 'late-size') {
            e.animations.prepare(e.window, target); e.window.move_frame(true, 100, 100); e.flush();
        } else prepareAndResize(e);
        assert.equal(e.animations._effects.size, 1);
        if (change === 'move') e.window.move_frame(true, 150, 100);
        else { e.window.rect.width = 390; e.window.emit('size-changed'); }
        assert.equal(e.animations._effects.size, 0);
        assert.equal(e.actor.transitions.size, 0); assert.equal(e.wm.completions, 0); e.balanced();
    }
});
test('refused resize followed by ordinary move, resize or public grab has no stale animation', () => {
    for (const interruption of ['move', 'resize', 'grab']) for (const beforeRedraw of [false, true]) {
        const e = environment(); e.animations.prepare(e.window, target);
        if (!beforeRedraw) e.flush();
        if (interruption === 'grab') e.display.emit('grab-op-begin', e.window, 1);
        else if (interruption === 'move') e.window.move_frame(true, 300, 250);
        else {
            // Ordinary interactive resize has a public grab, not SIZE_CHANGE.
            e.display.emit('grab-op-begin', e.window, 2);
            e.window.rect.width = 320; e.window.emit('size-changed');
        }
        e.flush(); assert.equal(e.animations._effects.size, 0);
        assert.equal(e.wm.completions, 0); e.balanced();
    }
});
test('refused resize followed by unrelated programmatic resize after redraw has no stale snapshot', () => {
    const e = environment(); e.animations.prepare(e.window, target); e.flush();
    e.window.rect.width = 320; e.window.emit('size-changed'); e.flush();
    assert.equal(e.animations._effects.size, 0); assert.equal(e.wm.completions, 0); e.balanced();
});
test('public grab cancels active overlay before interactive geometry changes', () => {
    const e = environment(); prepareAndResize(e);
    e.display.emit('grab-op-begin', e.window, 2);
    assert.equal(e.animations._effects.size, 0);
    e.window.rect.width = 333; e.window.emit('size-changed'); e.flush(); e.balanced();
});
test('constrained dimensions animate actual geometry, duplicate signals do not cancel', () => {
    const e = environment(); e.animations.prepare(e.window, target);
    e.window.move_resize_frame(true, 100, 100, 396, 288); e.flush();
    const effect = e.animations._effects.get(e.actor);
    assert.deepEqual({ ...effect.target }, e.window.get_frame_rect());
    assert.equal(effect.clone.get_transition('scale-x').target, 396 / 300);
    e.window.emit('size-changed'); e.window.emit('position-changed');
    assert.equal(e.animations._effects.get(e.actor), effect);
    e.finishSynthetic(); assert.equal(e.actor.freezes, 0); e.balanced();
});
test('no-op move and asynchronous refusal retain no frozen actor', () => {
    const e = environment(); e.animations.prepare(e.window, e.window.get_frame_rect());
    assert.equal(e.animations._effects.size, 0);
    e.animations.prepare(e.window, target); e.flush(); assert.equal(e.actor.frozen, 0); e.balanced();
});
test('synchronous ease completion and reduced motion are balanced', () => {
    for (const synchronous of [false, true]) for (const reduced of [false, true]) {
        const e = environment({ synchronous, reduced }); prepareAndResize(e);
        if (!synchronous) e.finishSynthetic();
        assert.equal(e.wm.completions, 0); e.balanced();
    }
});
test('foreign transitions survive synthetic preparation and cleanup', () => {
    const e = environment(); const foreign = {};
    e.actor.transitions.set('scale-x', foreign); e.animations.prepare(e.window, target);
    assert.equal(e.actor.get_transition('scale-x'), foreign); assert.equal(e.animations._effects.size, 0);
    e.actor.transitions.delete('scale-x'); prepareAndResize(e);
    // Live actor transitions are never ours, including ones installed mid-effect.
    e.actor.transitions.set('scale-x', foreign); e.animations.cancel(e.actor);
    assert.equal(e.actor.get_transition('scale-x'), foreign); e.balanced();
});
test('extension disable releases pending and active animations without native completion', () => {
    for (const active of [false, true]) {
        const e = environment();
        if (active) prepareAndResize(e); else e.animations.prepare(e.window, target);
        e.balanced(); assert.equal(e.wm.completions, 0);
    }
});

test('actual Shell void ease wrapper preserves completion cancellation and error reporting', async () => {
    for (const synchronous of [false, true]) {
        const e = environment({ synchronous });
        prepareAndResize(e);
        if (!synchronous) {
            assert.equal(e.animations._effects.size, 1);
            e.finishSynthetic();
        }
        assert.equal(e.animations._effects.size, 0);
        assert.equal(e.wm.completions, 0);
        await Promise.resolve();
        e.balanced();
    }
    const interrupted = environment();
    prepareAndResize(interrupted);
    interrupted.animations.cancel(interrupted.actor);
    await Promise.resolve();
    interrupted.balanced();

    const e = environment();
    // The real wrapper returns void even though its internal engine is Promise-based.
    assert.equal(e.actor.ease({}), undefined);
    const cancelled = { matches: (_domain, code) => code === 1 };
    e.actor.easeImpl = () => Promise.reject(cancelled);
    assert.equal(e.actor.ease({}), undefined);
    await Promise.resolve(); assert.equal(e.errors.length, 0);
    const unexpected = new Error('genuine ease failure');
    e.actor.easeImpl = () => Promise.reject(unexpected);
    assert.equal(e.actor.ease({}), undefined);
    await Promise.resolve(); assert.equal(e.errors.pop(), unexpected);
    e.balanced();

    // A synchronous engine failure still triggers _start's cleanup and rethrow.
    const failing = environment();
    failing.animations.prepare(failing.window, target);
    failing.window.move_resize_frame(true, target.x, target.y, target.width, target.height);
    const clone = failing.clones.at(-1);
    const failure = new Error('synchronous ease failure');
    clone.easeImpl = () => { throw failure; };
    assert.throws(() => failing.flush(), error => error === failure);
    assert.equal(failing.animations._effects.size, 0);
    failing.balanced();
});

// Explicit validation entry: do not invoke during source preparation/review.
// Exact names support failed-only retries without re-executing valid passes.
const selected = new Set(selectedNames);
assert.equal(selected.size, selectedNames.length, 'duplicate selected case');
for (const name of selected)
    assert(tests.some(test => test.name === name), `unknown selected case: ${name}`);
const runnable = selected.size ? tests.filter(test => selected.has(test.name)) : tests;
let failures = 0;
for (const { name, fn } of runnable) {
    try { await fn(); console.log(`PASS ${name}`); }
    catch (error) { failures++; console.error(`FAIL ${name}\n${error.stack}`); }
}
console.log(JSON.stringify({ cases: runnable.length, failures, skipped: tests.length - runnable.length }));
process.exitCode = failures ? 1 : 0;
