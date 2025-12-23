/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillUnmount, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class CourierTracker extends Component {
    setup() {
        this.state = useState({
            running: false,
            last: null,
            error: null,
            permission: null,
        });
        this._watchId = null;

        onWillUnmount(() => this.stop());
    }

    async _checkPermission() {
        try {
            if (navigator.permissions?.query) {
                const res = await navigator.permissions.query({ name: "geolocation" });
                this.state.permission = res.state;
            }
        } catch {
            // ignore
        }
    }

    async start() {
        this.state.error = null;
        if (this.state.running) return;

        if (!navigator.geolocation) {
            this.state.error = "Geolocation is not supported on this device/browser.";
            return;
        }

        if (!window.isSecureContext) {
            this.state.error = "This page is not a secure context. Use HTTPS to allow GPS in many browsers.";
            return;
        }

        await this._checkPermission();

        if (this._watchId !== null) {
            navigator.geolocation.clearWatch(this._watchId);
            this._watchId = null;
        }

        this._watchId = navigator.geolocation.watchPosition(
            async (pos) => {
                const c = pos.coords;
                this.state.last = `${c.latitude.toFixed(6)}, ${c.longitude.toFixed(6)} (±${Math.round(c.accuracy)}m)`;

                try {
                    await rpc("/delivery_yandex_gps/location/update", {
                        latitude: c.latitude,
                        longitude: c.longitude,
                        accuracy_m: c.accuracy,
                        speed_mps: c.speed,
                        heading: c.heading,
                    });
                } catch (e) {
                    this.state.error = `Server update failed: ${e?.message || e}`;
                }
            },
            (err) => {
                this.state.error = `GPS error ${err.code}: ${err.message || err}`;
                this.stop();
            },
            {
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 60000,
            }
        );

        this.state.running = true;
    }

    async stop() {
        // Tell server immediately so the manager removes the marker
        try {
            await rpc("/delivery_yandex_gps/location/stop", {});
        } catch {
            // ignore
        }

        if (this._watchId !== null) {
            navigator.geolocation.clearWatch(this._watchId); // stops watcher :contentReference[oaicite:3]{index=3}
            this._watchId = null;
        }
        this.state.running = false;
    }
}

CourierTracker.template = "delivery_yandex_gps.CourierTracker";
registry.category("actions").add("delivery_yandex_gps.courier_tracker", CourierTracker);
