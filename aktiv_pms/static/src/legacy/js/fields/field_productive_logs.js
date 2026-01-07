/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState,onMounted, onWillUnmount} from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";

//Popover logs template
class ProductiveLogsPopup extends Component {
    static template = "ProductiveLogs.PopoverContent";
    static props = {
        logs: { type: Array },
        close: { type: Function },
        openTask: { type: Function },
    };

    setup() {
        this.close = this.props.close;
        this.openTask = this.props.openTask;
    }
}

//Field widget template
export class field_productive_logs extends Component {
    static template = "web.field_productive_logs";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            logs: [],
        });
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "" });
        this.popover = usePopover(ProductiveLogsPopup, {
            position: "right-start",
        });

        this.scrollHandler = this.closePopoverOnScroll.bind(this);
        onMounted(() => {
            window.addEventListener('scroll', this.scrollHandler, true); // Use 'true' to capture event during capturing phase
        });

        onWillUnmount(() => {
            window.removeEventListener('scroll', this.scrollHandler, true);
        });
    }

    // format the value to show in hours amend column
    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        if (!value) return "";
        try {
            const data = JSON.parse(value);
            return data.length > 0 ? data[data.length - 1].new_hour : "";
        } catch (error) {
            console.error(_t("Error parsing value:", error));
            return "";
        }
    }

    // open the productive logs
    openProductiveLogs(ev) {
        const value = this.props.record.data[this.props.name];
        if (!value) {
            console.warn(_t("No data available for productive logs."));
            return;
        }
        try {
            const data = JSON.parse(value);
            this.state.logs = data;

            if (data && data.length > 0) {
                this.popover.open(ev.currentTarget,
                    {
                        logs: this.state.logs,
                        openTask: this.openTask.bind(this),
                        close: this.popover.close,
                    });
            } else {
                console.warn(_t("No logs available to display."));
            }
        } catch (error) {
            console.error(_t("Error opening productive logs:", error));
        }
    }

    // open the task
    openTask(ev) {
        ev.preventDefault();
        const task_id = this.props.record._values.task_id?.[0];
        if (task_id) {
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'project.task',
                res_id: task_id,
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            });
        } else {
            alert(_t("Task not defined to this timesheet"));
        }
    }

    // Close the popover when scrolling
    closePopoverOnScroll(event) {
        const timesheetElement = document.querySelector(".o_list_view"); // Adjust selector to your timesheet table
        if (timesheetElement && timesheetElement.contains(event.target)) {
            if (this.popover) {
                this.popover.close();
            }
        }
    }

}

export const FieldProductiveLogs = {
    component: field_productive_logs,
    displayName: _t("field_productive_logs"),
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};


registry.category("fields").add("field_productive_logs", FieldProductiveLogs);
