/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// Option 1 (preset):
// Car icon:
const ICON_PRESET = "islands#blueAutoIcon"; // :contentReference[oaicite:2]{index=2}
// If you prefer a delivery icon, use this instead:
// const ICON_PRESET = "islands#blueDeliveryIcon"; // :contentReference[oaicite:3]{index=3}

class CourierMap extends Component {
    setup() {
        this.mapEl = useRef("map");
        this._map = null;
        this._markers = new Map();
        this._timer = null;
        this._onResize = null;
        this._retryCount = 0;
        this._retryTimer = null;

        onMounted(() => this._start());
        onWillUnmount(() => this._stop());
    }

    async _loadYandex(apikey) {
        if (window.ymaps) return;

        await new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(apikey)}&lang=ru_RU`;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    async _waitForContainer(maxFrames = 600) {
        for (let i = 0; i < maxFrames; i++) {
            const el = this.mapEl.el;

            if (el) {
                if (el.offsetHeight === 0) {
                    el.style.width = "100%";
                    el.style.height = el.style.height || "75vh";
                    el.style.minHeight = el.style.minHeight || "450px";
                }

                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    return el;
                }
            }
            await new Promise((r) => requestAnimationFrame(r));
        }
        return null;
    }

    async _start() {
        try {
            const apikey = await rpc("/delivery_yandex_gps/yandex_key", {});
            await this._loadYandex(apikey);
            await new Promise((resolve) => window.ymaps.ready(resolve));

            const el = await this._waitForContainer();
            if (!el) {
                this._retryCount += 1;
                if (this._retryCount <= 5) {
                    this._retryTimer = setTimeout(() => this._start(), 500);
                    return;
                }
                throw new Error("Map container is not visible or has zero size.");
            }

            this._map = new window.ymaps.Map(
                el,
                { center: [41.3111, 69.2797], zoom: 11 },
                { autoFitToViewport: "always" }
            );

            this._map.container.fitToViewport();

            this._onResize = () => {
                if (this._map) {
                    try {
                        this._map.container.fitToViewport();
                    } catch {
                        // ignore
                    }
                }
            };
            window.addEventListener("resize", this._onResize);

            await this._refreshCouriers();
            this._timer = setInterval(() => this._refreshCouriers(), 2000);
        } catch (e) {
            console.error(e);
            throw e;
        }
    }

    async _refreshCouriers() {
        if (!this._map) return;

        const data = await rpc("/delivery_yandex_gps/location/list", {});
        const activeIds = new Set();

        for (const c of data) {
            if (c.lat !== null && c.lat !== undefined && c.lon !== null && c.lon !== undefined) {
                activeIds.add(c.courier_id);
                this._upsertMarker(c.courier_id, c.name, c.lat, c.lon, c.last_update);
            }
        }

        // Remove markers for couriers that are no longer active
        for (const [id, placemark] of this._markers.entries()) {
            if (!activeIds.has(id)) {
                this._map.geoObjects.remove(placemark);
                this._markers.delete(id);
            }
        }
    }

    _upsertMarker(id, name, lat, lon, ts) {
        if (!this._map) return;

        const label = `${name}${ts ? " (" + ts + ")" : ""}`;

        if (this._markers.has(id)) {
            const pm = this._markers.get(id);
            pm.geometry.setCoordinates([lat, lon]);
            pm.properties.set("balloonContent", label);
            pm.properties.set("hintContent", name);
            pm.properties.set("iconCaption", name);
        } else {
            // HERE is the only change for Option 1: preset -> car/delivery icon
            const pm = new window.ymaps.Placemark(
                [lat, lon],
                {
                    balloonContent: label,
                    hintContent: name,
                    iconCaption: name,
                },
                {
                    preset: ICON_PRESET, // :contentReference[oaicite:4]{index=4}
                }
            );
            this._map.geoObjects.add(pm);
            this._markers.set(id, pm);
        }
    }

    _stop() {
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }

        if (this._retryTimer) {
            clearTimeout(this._retryTimer);
            this._retryTimer = null;
        }

        if (this._onResize) {
            window.removeEventListener("resize", this._onResize);
            this._onResize = null;
        }

        if (this._map) {
            try {
                this._map.destroy();
            } catch {
                // ignore
            }
            this._map = null;
        }

        this._markers.clear();
    }
}

CourierMap.template = "delivery_yandex_gps.CourierMap";
registry.category("actions").add("delivery_yandex_gps.courier_map", CourierMap);
