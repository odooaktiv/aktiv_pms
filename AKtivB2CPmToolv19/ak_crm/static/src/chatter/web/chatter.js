/** @odoo-module **/
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {

    setup() {
        super.setup();
        this.action = useService("action");
        Object.assign(this.state, {
            leadType: null,
        });

        onWillStart(async () => {
            await this.getLeadType();
        });
    },

    async getLeadType() {
        if (this.props.threadId && this.props.threadModel === 'crm.lead') {
            const leadData = await this.orm.call(this.props.threadModel, "read", [[this.props.threadId], ['type']]);
            this.state.leadType = leadData && leadData[0] && leadData[0].type;
        }
    },

    openSendMail() {
        const action = {
            type: 'ir.actions.act_window',
            name: _t("Send Mail"),
            res_model: 'chatter.send.mail',
            view_mode: 'form',
            views: [[false, 'form']],
            context: {
                default_res_id: this.state.thread.id,
                default_res_model: this.state.thread.model,
                default_display_name: this.state.thread.name,
            },
            target: 'new',
        };
        this.action.doAction(action, {
            onClose: () => this.load(this.state.thread, ["activities", "messages"])
        });
    }
});
