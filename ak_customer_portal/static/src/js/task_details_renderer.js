/** @odoo-module **/

// In Odoo 19:
//   - @web/legacy/js/core/dialog was removed; Bootstrap 5 modals via window.Modal are used instead.
//   - rpc is no longer a service (bindService("rpc") fails); import it directly.
import { rpc } from "@web/core/network/rpc";
import publicWidget from '@web/legacy/js/public/public_widget';


publicWidget.registry.TaskDetailRenderer = publicWidget.Widget.extend({

    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click .task_separate_details': '_onClickTaskDetail',
        'click .sub_task_count': '_onClickSubTaskCount',
    }),

    selector: '#wrapwrap',

    /**
     * Create and show a Bootstrap 5 modal with the given title and HTML content.
     * Appended to document.body and auto-removed on hide.
     */
    _showModal(title, htmlContent) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        modal.querySelector('.modal-title').textContent = title;
        modal.querySelector('.modal-body').innerHTML = htmlContent;
        document.body.appendChild(modal);
        window.Modal.getOrCreateInstance(modal).show();
        modal.addEventListener('hidden.bs.modal', () => modal.remove(), { once: true });
        return modal;
    },

    _onClickTaskDetail(ev) {
        const taskDiv = ev.currentTarget;
        const taskId = parseInt(taskDiv.dataset.taskId);
        const taskName = taskDiv.dataset.taskName;
        rpc('/project/task/' + taskId, {}).then((html) => {
            this._showModal(`Task: ${taskName}`, html);
        }).catch((error) => {
            console.error('Error fetching task detail:', error);
        });
    },

    _onClickSubTaskCount(ev) {
        const taskDiv = ev.currentTarget;
        const taskId = parseInt(taskDiv.dataset.taskId);
        rpc('/project/sub_task/' + taskId, {}).then((html) => {
            const modal = this._showModal(`Task: ${taskDiv.dataset.taskName}`, html);
            modal.addEventListener('shown.bs.modal', () => {
                modal.querySelectorAll('tr.sub_task_details').forEach((tr) => {
                    tr.addEventListener('click', () => {
                        const trTaskId = parseInt(tr.dataset.taskId);
                        if (trTaskId) {
                            rpc('/project/task/' + trTaskId, {}).then((html) => {
                                this._showModal(`Task: ${tr.dataset.taskName}`, html);
                            });
                        }
                    });
                });
            }, { once: true });
        });
    },
});

export default publicWidget.registry.TaskDetailRenderer;
