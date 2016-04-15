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


Example Setup
-------------

1. Create support service
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/jira/ HTTP/1.1
    Content-Type: application/json
    Accept: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com

    {
        "name": "JIRA Support",
        "customer": "http://example.com/api/customers/eea999ddf31540aea6bd4f591aa353d1/",
        "backend_url": "https://jira.example.com/",
        "username": "username",
        "password": "password",
        "available_for_all": false
    }

2. Import support project
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/jira/a2f322fed8c444fab48547f595b34279/link/ HTTP/1.1
    Content-Type: application/json
    Accept: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com

    {
        "backend_id": "SPT",
        "project": "http://example.com/api/projects/e63838e3e68f4fc4aa39617b7550cef3/",
        "impact_field": "Impact",
        "reporter_field": "Original Reporter",
        "default_issue_type": "Support Request"
    }

3. Perform support actions
^^^^^^^^^^^^^^^^^^^^^^^^^^

Please use a project created about to post issues.
