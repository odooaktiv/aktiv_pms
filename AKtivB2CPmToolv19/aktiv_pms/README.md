Aktiv PMS
----------------
Odoo Version : Odoo 15.0

Installation
------------
Install the Application => Apps -> Aktiv PMS

Aktiv PMS
----------------

* This module will be used for project management.

Date 23/3/2022(Sahil_pms)
-----------------

- Work on solving the issue of the add a section functionality in the test cases and still unsolved.
- Work on the showing red line in the task tree view if the task planned hours more than the deadline given to complete
  the task.

Date 22/3/2022(Sahil_pms)
-----------------

- Work on wizard to be opened on click of "send for code review" button. Add new group for QA. Only QA and project
  manager has the access of edit, create , delete of test cases. Other user can only view them.
- work on adding Add a section inside test case. for adding the section in the tree view. And Fixing the code due to
  change done in adding the section. Due to which he count was incorrect for test cases.

Date 21/3/2022(Sahil_pms)
-----------------

- Complete working on setting of default developer in the task if there is only a single developer for the project.
- Work on making the task form readonly if login user is a project user only. And only allowing to edit the timesheet.

Date 17/3/2022(Sahil_pms)
-----------------

- Work on posting the message in the chatter when the Quality checks are performed in the wizard when the stage is
  changed.
- Worked on Customer field visibility to project manager. Visibility of configuration menu of project to the project
  manager. Remove add line option from the quality check wizard and the delete buttons. And setting default developer in
  task if there is only one developer in the project

Date 16/3/2022(Sahil_pms)
-----------------

- Worked on the wizard for quality check points and solved related issues.
- Worked on the changing of the state when all the quality check points are checked in the wizard.
- Worked on hiding the smart buttons from the project form view. And solving git conflicts.

Date 15/3/2022(Sahil_pms)
-----------------

- Worked on the show/hide of the test cases page when there is no record in it and if there is record then read only for
  states other than QA Testing.
- Worked on the wizard to check for the check points.
- Worked on the adding the stages in the project. To move from stage to another.

Date 14/3/2022(Sahil_pms)
-----------------

- Worked on the creation of new model Quality Analysis.

Date 14/3/2022
------------------

- Worked on customization of status bar in task form.
- Added buttons for changing the states.
- Worked on fetching of code reviewer and QA value from project form into task form when state changes.
- Worked on changing the color of test cases line inside the task form(if it is bug,then change to red and if it is
  expected then change to green)

Date 15/3/2022(Sruthy K S)
------------------

- Solved the issue of sequence incorrect generation in test cases lines inside task form using custom code.
- added fields inside test cases for counting total tasks performed,passed and failed.

Date 16/3/2022(Sruthy K S)
------------------

- worked on hiding some fields in task tree view and make the default view as tree instead of kanban.
- worked on showing states and task state changes based on boolean field.

Date 21/3/2022(Sruthy K S)
------------------

- worked on adding button "send for re-development" and added conditions for showing and hiding both "send for customer
  review" and 'send for redevelopment' button.
- changed the string of outcomes field.
- resolved issue when deleting multiple test case lines.
- resolved issue in wizard action and showing developer values.

Date 22/3/2022(Sruthy K S)
------------------

- Add boolean in test case.Description: This boolean is for visiblity of send for re-dev button-done
- In tree view of task. Task should be red if task's deadline is after two days and state should be "development"-done
- Task should be yellow if planned hours are less then 8 when state is "development"-done

Date 23/3/2022(Sruthy K S)
------------------
-worked on generating scheduled dates for meetings with duration days,weekly,monthly.
- monthly have some issue-checking on it.

Date 24/3/2022(Sruthy K S)
------------------
- solved issue in Generate meetings button click when duration is monthly.

Date 28/3/2022(Sruthy K S)
------------------
- worked on sending emails to the developers when task state changes.
- worked on hiding buttons except new and done when project type is consulting.

Date 29/3/2022(Sruthy K S)
------------------
- updated the reopened boolean field task and solved the issues.
- checked sending mails to developers when task state changes.Working fine.

Date 30/3/2022(Sruthy K S)
------------------
- worked on Change the field name Project type to task type and it should be editable.get Default type value from project but we can change it.-done.

Date 31/3/2022(Sruthy K S)
------------------
- worked on :-Add new field inside task type of many2many.

1) Developer - required
2) Code Reviewer -  should be mandatory if the state is development or re-development.
3) QA - should be visible if the state is Code review.:-done

-worked on :- - Inside the dropdown of developer field there should be only those users who are defined on project
- Inside the dropdown of code reviewers field there should be only those users who are defined on project
- Inside the dropdown of QA field there should be only those users who are defined on project
done.
- hided parent task and extra info
- Done Button should not visible in re-development state-done
- updated email code and checked-done.
- Visibility Of pdfwidge-updated.


Date 17/3/2022(Sruthy K S)
------------------

- removed default value of developer inside task form.

Date 11/3/2022(Sahil_pms)
------------------

- Worked on adding new fields that will be mandatory to change the satge.
- Worked on the access rights of the user if he/she is involved in the project as developer, QA or Code Reviwer.
- Worked on fixing the field names and view issues.
- Worked on hide the fields on the tree if the project user.
- Worked on add button to move the stage from initial stage.

Date 10/3/2022
------------------

- Code Review and done necessary chages in project task model and views.
- Add domain on devloper field of project task to return only those users who are set as a devloper, code reviewer and
  QA in project task.

Date 03/06/2022
-------------------

- Add one Boolean Field in Project.Task model and Field name is "Billed Hours".
- Add one Invisible Boolean Field in "timesheet_ids" in "Timesheet" page .Field name is qa_timesheet.
- Add Filter and Group by for billed_hours Field in project.task Model. 

Date 06/06/2022 and 07/06/2022
-------------------
- Take sub-tasks total hours below the Initially planned hours. Right now the field is in timesheet tab.
- Need to add one new filed called QA Timesheet at timesheet and if login user or employee of those entries are QA that boolean will set as true automatically.
- Add a menu named Basic Guidelines in Project Menu. This menu should be visisble to all the Users. Create a tree view which will have the following fields
  1) Name - Char
  2) Link - Text field
- Need to add filter and group by of timesheet entries with that boolean (in list view of timesheet )
- Test case field should be editable from starting, right now when the stage goes to the QA than only the field is editable
- Add a boolean in a task named "Is Bug", if this is true than there should only 2 stages
  1) New
  2) Done

Date 06/06/2022
--------------------

- Add functions to connect PM tool.
- Add dynamic selection for task which will fetch task and its id from PM tool.
- Add button and onclick of that button all the non synced entries of the current login user will be synced on PM tool.



Odoo V17.0.1.0.1 ---- > V17.0.1.0.1
=========================
Date 21/Apirl/2025(Muthaiyan Selvam)
--------------------

- Modified the field label names inside the "aktiv_pms module"
Project Owner --> Project lead
Tech Lead --> Lead Engineer
