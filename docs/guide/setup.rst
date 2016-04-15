Configuration
-------------

NodeConductor can integrate with Atlassian JIRA to provide support to the end-users.

Expected structure for the JIRA project is as follows:

- Existing issue type: Support Request (must be default issue type for the project)
- Custom fields:

  * Impact, type: Text Field (single line)
  * Original Reporter, type: Text Field (single line)

Expected permissions:

+-------------------+------------------+
| Permission        | Permission code  |
+===================+==================+
| Add Comments      | COMMENT_ISSUE    |
+-------------------+------------------+
| Edit Own Comments | COMMENT_EDIT_OWN |
+-------------------+------------------+
| Browse Projects   | BROWSE           |
+-------------------+------------------+


WebHook Setup
-------------

It's possible to track updates of JIRA issues and apply them to NodeConductor immediately.

An instruction of JIRA configuration can be found at
https://developer.atlassian.com/jiradev/jira-apis/webhooks

WebHook URL should be defined as `http://nodeconductor.example.com/api/jira-webhook-receiver/`
and following events enabled:

* issue created
* issue updated
* issue deleted
