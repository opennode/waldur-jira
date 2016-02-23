Installation
------------

* `Install NodeConductor <http://nodeconductor.readthedocs.org/en/latest/guide/intro.html#installation-from-source>`_

* Clone NodeConductor Jira repository

  .. code-block:: bash

    git clone https://github.com/opennode/nodeconductor-jira.git

* Install NodeConductor Jira into NodeConductor virtual environment

  .. code-block:: bash

    cd /path/to/nodeconductor-jira/
    python setup.py install

Configuration
-------------

NodeConductor can integrate with Atlassian JIRA to provide support to
the end-users. To enable integration, JIRA settings should be added, for example:

.. code-block:: python

    NODECONDUCTOR_JIRA = {
        'server': 'https://jira.example.com/',
        'username': 'alice@example.com',
        'password': 'password',
        'project': 'NST',
    }

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
