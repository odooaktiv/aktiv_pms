/** @odoo-module **/

import Dialog from "@web/legacy/js/core/dialog";
import publicWidget from '@web/legacy/js/public/public_widget';


publicWidget.registry.TaskDetailRenderer = publicWidget.Widget.extend({

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click .task_separate_details': '_onClickTaskDetail',
        'click .sub_task_count': '_onClickSubTaskCount'
    }),

    selector: '#wrapwrap',

    _onClickTaskDetail (ev) {
        const $taskDiv = $(ev.currentTarget);
        const taskId = parseInt($taskDiv.data('task-id'));
        const taskName = $taskDiv.data('task-name');
        const url = "/project/task/" + taskId
        this.rpc(url, {}
        ).then((html) => {
            const $content = $(html);
            new Dialog(this, {
                title: `Task: ${taskName}`,
                size: 'extra-large',
                $content: $content,
                buttons: [{
                    text: 'Close',
                    close: true,
                }],
            }).open();
        }).catch((error) => {
            console.error('Error fetching task detail:', error);
        });
        
    },

    _onClickSubTaskCount (ev) {
        var self = this;
        const $taskDiv = $(ev.currentTarget);
        const taskId = parseInt($taskDiv.data('task-id'));
        const url = "/project/sub_task/" + taskId
        this.rpc(url, {}).then(function(html) {
            var $content = $(html);
            var dialog = new Dialog(this, {
                title: `Task: ${$taskDiv.data('task-name')}`,
                size: 'extra-large',
                $content: $content,
                buttons: [{
                    text: 'Close',
                    close: true
                }]
            });
            dialog.opened().then(function() {
                dialog.$('tr.sub_task_details').click(function() {
                    var tr_tag = $(this);
                    if (tr_tag.attr('data-task-id')) {
                        var tr_task_id = parseInt(tr_tag.attr('data-task-id'));
                        var url = "/project/task/" + tr_task_id
                        self.rpc(url, {}).then(function(html) {
                            var $content = $(html);
                            new Dialog(self, {
                                title: `Task: ${tr_tag.attr('data-task-name')}`,
                                size: 'extra-large',
                                $content: $content,
                                buttons: [{
                                    text: 'Close',
                                    close: true
                                }]
                            }).open();
                        });
                    };
                });
            });
            dialog.open();
        });
    },
});

export default publicWidget.registry.TaskDetailRenderer;
