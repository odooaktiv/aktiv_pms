import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AktivOdooDays = publicWidget.Widget.extend({
    selector: ".odoo_days_page",
    events: {
        "change .objectives_options": "_changeObjectives",
    },

    /**
     * @override
     */
    start: function () {
        return this._super.apply(this, arguments);
    },

    _changeObjectives: function (ev) {
        const form = this.el.querySelector(".odoo_days_contest_form");
        if (!form) {
            return;
        }
        const objectivesInput = form.querySelector("[name='objectives']");
        const input = ev.currentTarget;
        let objectiveVals = [];
        if (objectivesInput.value) {
            try {
                objectiveVals = JSON.parse(objectivesInput.value);
            } catch (err) {
                objectiveVals = [];
            }
        }
        const inputVal = input.value;
        if (input.checked) {
            if (!objectiveVals.includes(inputVal)) {
                objectiveVals.push(inputVal);
            }
        } else {
            const idx = objectiveVals.indexOf(inputVal);
            if (idx >= 0) {
                objectiveVals.splice(idx, 1);
            }
        }
        objectivesInput.value = objectiveVals.length ? JSON.stringify(objectiveVals) : "";
    },
});
