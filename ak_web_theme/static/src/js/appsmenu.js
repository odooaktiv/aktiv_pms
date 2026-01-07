/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AppsMenu } from "@muk_web_theme/webclient/appsmenu/appsmenu";

patch(AppsMenu.prototype, {
    onDropdownStateChanged(args){
        if(this.rootRef.el && args.emitter.rootRef.el && !($(args.emitter.rootRef.el).hasClass('o_navbar_apps_menu')) && $(this.rootRef.el).hasClass('o_navbar_apps_menu') && $(this.rootRef.el).hasClass('show')){
            return;
        }
        return super.onDropdownStateChanged(...arguments);
    },
    onWindowClicked(ev) {
        if(this.state.open && !(ev.target.classList.contains('o_navbar_apps_menu'))){
            return;
        }
        return super.onWindowClicked(ev);
    },
});



