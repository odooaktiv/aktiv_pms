/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { cookie } from "@web/core/browser/cookie";

export const userColorSchemeService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        const pallets = session.color_scheme_pallets || {};

        const userColorSchemes = pallets.color_schemes || [];
        const allowUserColorScheme = pallets.allow_user_color_scheme || false;

        const colorScheme = cookie.get("color_scheme");

        let currentUserColorScheme = false;
        if (!colorScheme || colorScheme === "light") {
            currentUserColorScheme = pallets.current_color_scheme || false;
        } else {
            currentUserColorScheme = pallets.current_color_scheme_dark || false;
        }

        return {
            userColorSchemes,
            currentUserColorScheme,
            allowUserColorScheme,

            async setUserColorScheme(schemeId) {
                await orm.call("res.users", "set_user_color_scheme", [[user.userId], schemeId || false]);
                browser.setTimeout(() => browser.location.reload(), 200);
            },
        };
    },
};

registry.category("services").add("user_color_scheme", userColorSchemeService);
