/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class userColorSchemeSelector {
    constructor(userColorSchemeService, toggleDelay) {
        this.userColorSchemeService = userColorSchemeService;
    }

    switchUserColorScheme(schemeId) {
		this.userColorSchemeService.setUserColorScheme(schemeId)
    }
}

export class SwitchUserColorSchemeItem extends Component {
    static template = "ak_color_scheme.SwitchUserColorSchemeItem";
    static components = { DropdownItem, SwitchUserColorSchemeItem };
    static props = {
		color: {},
        level: { type: Number },
    };

    setup() {
        this.userColorSchemeService = useService("user_color_scheme");
        this.userColorSchemeSelector = useState(this.env.userColorSchemeSelector);
    }

    get isUserColorSchemeCurrent() {
        return this.props.color.id === this.userColorSchemeService.currentUserColorScheme[0];
    }

    toggleUserColorScheme() {
        this.userColorSchemeSelector.switchUserColorScheme(this.props.color.id);
    }
}

export class SwitchUserColorSchemeMenu extends Component {
    static template = "ak_color_scheme.SwitchUserColorSchemeMenu";
    static components = { Dropdown, DropdownItem, SwitchUserColorSchemeItem };
    static props = {};
    static toggleDelay = 1000;

    setup() {
        this.userColorSchemeService = useService("user_color_scheme")
        this.userColorSchemeSelector = useState(new userColorSchemeSelector(this.userColorSchemeService, this.constructor.toggleDelay));
        useChildSubEnv({ userColorSchemeSelector: this.userColorSchemeSelector });
    }
    toggleUserColorSchemeDefault() {
        this.userColorSchemeSelector.switchUserColorScheme();
    }
};

registry.category("systray").add("SwitchUserColorSchemeMenu", {Component: SwitchUserColorSchemeMenu}, { sequence: 2 });