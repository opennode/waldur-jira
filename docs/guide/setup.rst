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
