/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { busService } from "@bus/services/bus_service";

export class FetchTimesheetEntries extends Component {
    static components = { Dropdown };
    static props = {
        placeholder: { type: String, optional: true },
    };

    setup() {
//        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            timesheetEntries: [],
            error: null,
            sync : false,
            activeTab : 'all',
            counter: 0,
                    });

        this.uid = useService("user")['userId'];

//         Fetch entries when component is mounted
        onMounted(async () => {
            await this.fetchTimesheetEntries();
            await this.updateCounter();
            this.setupUpCounter();
        });

        onWillUnmount(() => {
            this.cleanupUpCounter();
        });
    }

    setupUpCounter() {
        const channel = `unsync_timesheet_update_${this.uid}`;
        this.env.services.bus_service.addChannel(channel);
        this.env.services.bus_service.addEventListener('notification', this.handleNotification.bind(this));

    }

    cleanupUpCounter() {
        if (this.busService) {
            const channel = `unsync_timesheet_update_${this.uid}`;
            this.busService.removeChannel(channel);
            this.busService.removeEventListener('notification', this.handleNotification.bind(this));
        }
    }

    async handleTimesheetSystrayClick() {
        this.state.sync = false;
        await this.fetchTimesheetEntries();
    }


    async handleNotification(event) {
    // Extract the actual notifications from event.detail
        const notifications = event.detail;

        if (!Array.isArray(notifications)) {
            console.error('Expected an iterable notifications object, but received:', notifications);
            return;
        }

        for (const { payload, type } of notifications) {
            if (type === 'unsync_timesheet_update' && payload.user_id === this.uid) {
                if (payload.action === 'update_counter') {
                    // Only trigger the counter update if the action is specifically 'update_counter'
                    await this.updateCounter();
                }
            }
        }
    }

    async updateCounter() {
        const unsync_search_domain = [['user_id', '=', this.uid], ['data_sync', '=', 'not_sync'], ['date', '>=', '2024-03-01']];
        const unsync_search_count = await this.orm.searchCount("account.analytic.line", unsync_search_domain);
        const count = unsync_search_count
        this.state.counter = count;  // Update the counter in the state
        await this.fetchTimesheetEntries();
    }


    async syncTimesheetEntries(){
         try {
            const function_call = await this.orm.silent.call("project.task", "action_sync_timesheet_pm_tool", [this.uid]);
            const unsync_search_domain = [['user_id', '=', this.uid], ['data_sync', '=', 'not_sync'], ['date', '>=', '2024-03-01']];
            const unsync_search_count = await this.orm.searchCount("account.analytic.line", unsync_search_domain);
            const count = unsync_search_count
            if (count === 0) {
                this.state.sync = true;
            } else {
                this.state.sync = false;
                await this.fetchTimesheetEntries();
            }
        } catch (error) {
            console.error('Failed to sync timesheet entries:', error);
        }
    }


    async groupEntriesByDate(result) {
        try {

            this.activeTab = 'date_range';
            if (!Array.isArray(result) || result.length === 0) {
                this.state.dateGroupedEntries = ""
                console.error("No timesheet entries found or invalid result format");
                return;
            }

            // Group entries by date
            const groupedByDate = result.reduce((acc, entry) => {
                const date = this.formatDate(entry.date);
                const taskId = entry.task_id ? entry.task_id[0] : null;
                const taskName = entry.task_id ? entry.task_id[1] : 'No Task';
                const projectId = entry.project_id ? entry.project_id[0] : null;
                const projectName = entry.project_id ? entry.project_id[1] : 'No Project';

                if (!acc[date]) {
                    acc[date] = {
                        date,
                        entryCount: 0,
                        projects: new Map(),
                        tasks: new Map(),
                        totalHours: 0
                    };
                }

                // Update entry count and total hours
                acc[date].entryCount++;
                acc[date].totalHours += entry.unit_amount;

                // Update projects
                if (!acc[date].projects.has(projectId)) {
                    acc[date].projects.set(projectId, { id: projectId, name: projectName, taskCount: 0, entryCount: 0, totalHours: 0 });
                }
                let project = acc[date].projects.get(projectId);
                project.entryCount++;
                project.totalHours += entry.unit_amount;

                // Update tasks
                if (!acc[date].tasks.has(taskId)) {
                    acc[date].tasks.set(taskId, { id: taskId, name: taskName, projectId, projectName, entryCount: 0, totalHours: 0 });
                    project.taskCount++;
                }
                let task = acc[date].tasks.get(taskId);
                task.entryCount++;
                task.totalHours += entry.unit_amount;

                return acc;
            }, {});

            // Convert grouped data to array and calculate final counts
            const dateGroupedEntries = Object.values(groupedByDate).map(group => ({
                date: group.date,
                entryCount: group.entryCount,
                projectCount: group.projects.size,
                taskCount: group.tasks.size,
                totalHours: group.totalHours,
                projects: Array.from(group.projects.values()),
                tasks: Array.from(group.tasks.values())
            }));

            if (dateGroupedEntries.length === 0) {
                console.warn("No entries after grouping. Check if data is being filtered out.");
            } else {
                console.log(`Total number of grouped dates: ${dateGroupedEntries.length}`);
            }

            // Sort dateGroupedEntries by date in descending order
            dateGroupedEntries.sort((a, b) => new Date(b.date) - new Date(a.date));

            // Update state
            console.log("Date Grouped Entries", dateGroupedEntries)
            this.state.dateGroupedEntries = dateGroupedEntries;

            return { dateGroupedEntries };  // Return the data for external use if needed
        } catch (error) {
            console.error('Failed to fetch or process timesheet entries:', error);
            this.state.error = error.message || "Failed to fetch or process timesheet entries";
            throw error;  // Re-throw the error for the caller to handle
        }
    }



    async fetchProjectGroups(result) {
        try {
            if (!result || !Array.isArray(result)) {
                console.error('Invalid timesheet entries data');
                return;
            }
            //  Extract the project and task data
            const projectTaskMap = result.reduce((acc, entry) => {
                const projectId = entry.project_id && entry.project_id[0];
                const projectName = entry.project_id && entry.project_id[1];
                const taskId = entry.task_id && entry.task_id[0];
                const taskName = entry.task_id && entry.task_id[1];

                if (!projectId || !projectName) return acc;
            //   Adding the project and the existing or not
                if (!acc[projectId]) {
                    acc[projectId] = {
                        id: projectId,
                        name: projectName,
                        tasks: {},
                        taskCount: 0,
                        entryCount: 0
                    };
                }

                acc[projectId].entryCount++;
        //   Adding the tasks to the appropriate project
                if (taskId && taskName) {
                    if (!acc[projectId].tasks[taskId]) {
                        acc[projectId].tasks[taskId] = {
                            id: taskId,
                            name: taskName,
                            count: 0,
                            entries: []
                        };
                        acc[projectId].taskCount++;

                    }

                    acc[projectId].tasks[taskId].entries.push({
                        id: entry.id,
                        name: entry.name,
                        date: entry.date,
                        unit_amount: entry.unit_amount
                    });
                    acc[projectId].tasks[taskId].count++;
                }

                return acc;
            }, {});
        //   Prepare the list of the records
            const projectList = Object.values(projectTaskMap).map(project => ({
                id: project.id,
                name: project.name,
                taskCount: project.taskCount,
                entryCount: project.entryCount,
                tasks: Object.values(project.tasks)
            }));

            this.state.projectList = projectList;
            return projectList;
        } catch (error) {
            console.error('Project Error:', error);
            return [];
        }
    }

    get counter() {
        return this.state.counter;
    }

    formatFloatTime(floatTime) {
        const hours = Math.floor(floatTime);
        const minutes = Math.round((floatTime - hours) * 60);
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    }



    async fetchTimesheetEntries() {
        try {
            const fields = ["name", 'date', 'unit_amount', 'project_id', 'task_id', 'id'];
            const domain = [['project_id', '!=', false],['user_id', '=', this.uid],['data_sync', '=', 'not_sync'],
            ['date', '>=', '2024-03-01']];
            const result = await this.orm.searchRead("account.analytic.line", domain, fields, {
                limit: 300
            });

            // Filter the project list
            this.fetchProjectGroups(result);
            this.groupEntriesByDate(result);

            this.state.timesheetEntries = result.map(entry => {
                entry.formattedDate = this.formatDate(entry.date);
                return entry;
            });
        } catch (error) {
            this.state.error = error.message || "Failed to fetch timesheet entries";
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const year = date.getFullYear();
        return `${month}/${day}/${year}`;
    }
}

FetchTimesheetEntries.template = "ak_timesheet_systray.FetchTimesheetEntries";

registry.category("systray").add("FetchTimesheetEntries", {
    Component: FetchTimesheetEntries
}, {
    sequence: 2
});
