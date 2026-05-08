/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


class UserColorSchemeSelector {
    constructor(userColorSchemeService) {
        this.userColorSchemeService = userColorSchemeService;
    }

    async switchUserColorScheme(schemeId = false) {
        await this.userColorSchemeService.setUserColorScheme(schemeId);
    }
}


export class SwitchUserColorSchemeItem extends Component {
    static template = "ak_color_scheme.SwitchUserColorSchemeItem";
    static components = { DropdownItem };

    static props = {
        color: { type: Object },
        level: { type: Number },
    };

    setup() {
        this.userColorSchemeService = useService("user_color_scheme");
        this.userColorSchemeSelector = useState(this.env.userColorSchemeSelector);
    }

    get isUserColorSchemeCurrent() {
        return (
            this.userColorSchemeService.currentUserColorScheme &&
            this.userColorSchemeService.currentUserColorScheme[0] === this.props.color.id
        );
    }

    async toggleUserColorScheme() {
        await this.userColorSchemeSelector.switchUserColorScheme(this.props.color.id);
        window.location.reload();
    }
}


export class SwitchUserColorSchemeMenu extends Component {
    static template = "ak_color_scheme.SwitchUserColorSchemeMenu";
    static components = { Dropdown, DropdownItem, SwitchUserColorSchemeItem };

    setup() {
        this.userColorSchemeService = useService("user_color_scheme");

        this.userColorSchemeSelector = useState(
            new UserColorSchemeSelector(this.userColorSchemeService)
        );

        useChildSubEnv({ userColorSchemeSelector: this.userColorSchemeSelector });
    }

    async toggleUserColorSchemeDefault() {
        await this.userColorSchemeSelector.switchUserColorScheme(false);
        window.location.reload();
    }
}

registry.category("systray").add(
    "ak_color_scheme.SwitchUserColorSchemeMenu",
    { Component: SwitchUserColorSchemeMenu },
    { sequence: 2 }
);
