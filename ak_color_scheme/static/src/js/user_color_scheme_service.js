/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { cookie } from "@web/core/browser/cookie";
import { jsonrpc } from "@web/core/network/rpc_service";
import { useService } from "@web/core/utils/hooks";


export const userColorSchemeService = {
    dependencies: ["rpc", "user"],
    async start(env, { rpc, user }) {
        const userColorSchemes = session.color_scheme_pallets.color_schemes
        this.colorScheme = cookie.get("color_scheme")
        this.currentUserColorScheme = ""
		if (!this.colorScheme || this.colorScheme === 'light') {
			this.currentUserColorScheme = session.color_scheme_pallets.current_color_scheme
		}
		else {
			this.currentUserColorScheme = session.color_scheme_pallets.current_color_scheme_dark
		}
        return {
			userColorSchemes,
			currentUserColorScheme: this.currentUserColorScheme,
			allowUserColorScheme: session.color_scheme_pallets.allow_user_color_scheme,
			setUserColorScheme(schemeId) {
				rpc("/web/dataset/call_kw/res.users/set_user_color_scheme", {
	                model: "res.users",
	                method: "set_user_color_scheme",
	                args: [user.userId, schemeId],
		            kwargs: {},
	            }).then(function () {
	                browser.setTimeout(() => browser.location.reload());
	            });
            },
        };
    },
};

registry.category("services").add("user_color_scheme", userColorSchemeService);
