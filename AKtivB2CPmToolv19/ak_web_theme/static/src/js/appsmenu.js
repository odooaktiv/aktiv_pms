/** @odoo-module **/
import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { AppsMenu } from "@muk_web_theme/webclient/appsmenu/appsmenu";

// Patch AppsMenu to control navbar open state via CSS class
// and prevent accidental close on click-away (enterprise-like full-screen menu)
patch(AppsMenu.prototype, {
    setup() {
        super.setup();
        // Toggle `o_apps_menu_open` class on navbar based on menu state.
        // This drives the CSS morph animation (grid → back arrow) and
        // hides menu sections / brand while the apps menu is open.
        useEffect(
            (isOpen) => {
                const navbar = document.querySelector(".o_main_navbar");
                if (navbar) {
                    navbar.classList.toggle("o_apps_menu_open", isOpen);
                }
                return () => {
                    if (navbar) {
                        navbar.classList.remove("o_apps_menu_open");
                    }
                };
            },
            () => [this.state?.isOpen]
        );
    },
    // Prevent the apps menu from closing on click-away.
    // The full-screen home menu should only close via:
    //   - toggle button click (handled by Dropdown.handleClick)
    //   - app selection (handled by ACTION_MANAGER:UI-UPDATED bus event)
    popoverCloseOnClickAway() {
        return false;
    },
    onOpened() {
        super.onOpened();
    },
});
