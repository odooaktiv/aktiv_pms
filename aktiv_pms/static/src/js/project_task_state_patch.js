/** @odoo-module */
import { ProjectTaskStateSelection } from "@project/components/project_task_state_selection/project_task_state_selection";
import { patch } from "@web/core/utils/patch";

/**
 * aktiv_pms replaces project.task `state` with custom values (new, dev, approval…)
 * that are incompatible with ProjectTaskStateSelection, which is hardcoded for the
 * v19 standard states (01_in_progress, 04_waiting_normal, etc.).
 *
 * This patch makes the component safe by deriving both options and label directly
 * from the field's own selection definition instead of v19 standard state names.
 */
patch(ProjectTaskStateSelection.prototype, {
    get options() {
        return this.props.record.fields[this.props.name]?.selection || [];
    },
    get label() {
        const currentValue = this.currentValue;
        const found = this.options.find(([v]) => v === currentValue);
        return found ? found[1] : String(currentValue || "");
    },
});
