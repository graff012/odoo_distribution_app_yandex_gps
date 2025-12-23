/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// Store singleton on window so it survives hot reloads and multiple action mounts.
const GLOBAL_KEY = "__deliveryYandexGpsTracker__";
const LS_KEY = "delivery_yandex_gps.intent";

function safeGetIntent() {
    try {
        return localStorage.getItem(LS_KEY) === "1";
    } catch {
        return false;
    }
}

function safeSetIntent(v) {
    try {
        localStorage.setItem(LS_KEY, v ? "1" : "0");
    } catch {
        // ignore
    }
}

function createTracker() {
    let intent = safeGetIntent();
    let watchId = null;

    let last = null;
    let error = null;

    let retryTimer = null;
    let heartbeatTimer = null;
    let bootPromise = null;

    const listeners = new Set();

    function snapshot() {
        return { running: intent, last, error };
    }

    function notify() {
        const s = snapshot();
        for (const cb of listeners) cb(s);
    }

    function setIntent(v) {
        intent = !!v;
        safeSetIntent(intent);
        notify();
    }

    function startHeartbeat() {
        if (heartbeatTimer) return;
        heartbeatTimer = setInterval(async () => {
            try {
                await rpc("/delivery_yandex_gps/location/ping", {});
            } catch {
                // ignore transient network errors
            }
        }, 30000);
    }

    function stopHeartbeat() {
        if (heartbeatTimer) {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
        }
    }

    async function bootstrapFromServer() {
        if (bootPromise) return bootPromise;
        bootPromise = (async () => {
            try {
                const st = await rpc("/delivery_yandex_gps/location/state", {});
                setIntent(!!st.is_tracking);
            } catch {
                // If offline, keep localStorage intent
            }

            if (intent) {
                startHeartbeat();
                await ensureWatch();
            }
        })();
        return bootPromise;
    }

    async function ensureWatch() {
        if (!intent) return;

        if (!navigator.geolocation) {
            error = "Geolocation is not supported on this device/browser.";
            notify();
            return;
        }

        // Many browsers require secure context for geolocation.
        if (!window.isSecureContext) {
            error = "Not a secure context. Use HTTPS (localhost is OK for development).";
            notify();
            return;
        }

        if (watchId !== null) return;

        watchId = navigator.geolocation.watchPosition(
            async (pos) => {
                const c = pos.coords;

                last = `${c.latitude.toFixed(6)}, ${c.longitude.toFixed(6)} (±${Math.round(c.accuracy)}m)`;
                error = null;
                notify();

                try {
                    await rpc("/delivery_yandex_gps/location/update", {
                        latitude: c.latitude,
                        longitude: c.longitude,
                        accuracy_m: c.accuracy,
                        speed_mps: c.speed,
                        heading: c.heading,
                    });
                } catch (e) {
                    // Keep watching; just surface the server error
                    error = `Server update failed: ${e?.message || e}`;
                    notify();
                }
            },
            async (errObj) => {
                const code = errObj?.code;
                const msg = errObj?.message || String(errObj);

                // Codes are standardized (1 denied, 2 unavailable, 3 timeout). :contentReference[oaicite:3]{index=3}
                const gps_status = code === 1 ? "denied" : "unavailable";

                try {
                    await rpc("/delivery_yandex_gps/location/ping", {
                        gps_status,
                        error_code: code,
                        error_message: msg,
                    });
                } catch {
                    // ignore
                }

                if (code === 1) {
                    // Permission denied => stop intent (courier must re-enable permission)
                    error = `GPS permission denied: ${msg}`;
                    notify();
                    await stop(true);
                    return;
                }

                // Unavailable/timeout => keep intent ON, retry later
                error = `GPS unavailable (code ${code}): ${msg} (will retry)`;
                notify();

                if (watchId !== null) {
                    navigator.geolocation.clearWatch(watchId);
                    watchId = null;
                }

                if (retryTimer) clearTimeout(retryTimer);
                retryTimer = setTimeout(() => {
                    if (intent) ensureWatch();
                }, 5000);
            },
            { enableHighAccuracy: true, maximumAge: 0, timeout: 60000 }
        );
    }

    async function start() {
        setIntent(true);
        startHeartbeat();

        try {
            await rpc("/delivery_yandex_gps/location/start", {});
        } catch {
            // ignore; heartbeat/update will set state when network returns
        }

        await ensureWatch();
    }

    async function stop(notifyServer) {
        if (notifyServer) {
            try {
                await rpc("/delivery_yandex_gps/location/stop", {});
            } catch {
                // ignore
            }
        }

        stopHeartbeat();

        if (retryTimer) {
            clearTimeout(retryTimer);
            retryTimer = null;
        }

        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }

        setIntent(false);
    }

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && intent && watchId === null) {
            ensureWatch();
        }
    });

    function subscribe(cb) {
        listeners.add(cb);
        cb(snapshot());
        return () => listeners.delete(cb);
    }

    return { start, stop, subscribe, bootstrapFromServer };
}

const tracker = (window[GLOBAL_KEY] ||= createTracker());

class CourierTracker extends Component {
    setup() {
        this.state = useState({
            running: false, // intent
            last: null,
            error: null,
        });

        this._unsubscribe = tracker.subscribe((s) => {
            this.state.running = s.running;
            this.state.last = s.last;
            this.state.error = s.error;
        });

        onMounted(async () => {
            await tracker.bootstrapFromServer();
        });

        onWillUnmount(() => {
            if (this._unsubscribe) this._unsubscribe();
        });
    }

    async start() {
        await tracker.start();
    }

    async stop() {
        await tracker.stop(true);
    }
}

CourierTracker.template = "delivery_yandex_gps.CourierTracker";
registry.category("actions").add("delivery_yandex_gps.courier_tracker", CourierTracker);
