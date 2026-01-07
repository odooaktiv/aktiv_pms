/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.AktivOdooDays = publicWidget.Widget.extend({
    selector: '.odoo_days_page',
    events: {
        'change .objectives_options': '_changeObjectives',
    },

    // events: Object.assign({}, publicWidget.Widget.prototype.events, {
    //     'click .task_separate_details': '_onClickTaskDetail',
    //     'click .sub_task_count': '_onClickSubTaskCount'
    // }),

    /**
     * @override
     */
    start: function () {
        var start = this._super.apply(this, arguments);
        return start
    },
    _changeObjectives: function(e){
        let $form = $(".odoo_days_contest_form");
        let $input = $(e.currentTarget)
        let objectives = $form.find("[name='objectives']")
        let objective_vals = objectives.val()
        if (!objective_vals){
            objective_vals = []
        }
        else{
            objective_vals = JSON.parse(objectives.val())
        }
        let input_val = $input.val()
        if ($input.is(":checked"))
        {
            if ($.inArray(input_val, objective_vals) < 0){
                objective_vals.push(input_val)
            }
        }
        else
        {
            objective_vals.splice($.inArray(input_val, objective_vals), 1);
        }
        if (!objective_vals.length){
            objectives.val('')
        }
        else{
            objectives.val(JSON.stringify(objective_vals))
        }
    },

});
