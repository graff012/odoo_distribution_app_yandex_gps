/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class CourierMap extends Component {
    setup() {
        this.mapEl = useRef("map");
        this._map = null;
        this._markers = new Map();
        this._timer = null;
        this._onResize = null;

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

    async _waitForContainer(maxFrames = 120) {
        for (let i = 0; i < maxFrames; i++) {
            const el = this.mapEl.el;
            if (el && el.offsetWidth > 0 && el.offsetHeight > 0) {
                return el;
            }
            await new Promise((r) => requestAnimationFrame(r));
        }
        throw new Error("Map container is not visible or has zero size.");
    }

    async _start() {
        const apikey = await rpc("/delivery_yandex_gps/yandex_key", {});
        await this._loadYandex(apikey);
        await new Promise((resolve) => window.ymaps.ready(resolve));

        const el = await this._waitForContainer();

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

        // Remove markers for couriers no longer active
        for (const [id, placemark] of this._markers.entries()) {
            if (!activeIds.has(id)) {
                this._map.geoObjects.remove(placemark); // remove from map :contentReference[oaicite:4]{index=4}
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
            pm.properties.set("iconCaption", name);
        } else {
            const pm = new window.ymaps.Placemark(
                [lat, lon],
                { balloonContent: label, iconCaption: name },
                { preset: "islands#blueDotIconWithCaption" }
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
