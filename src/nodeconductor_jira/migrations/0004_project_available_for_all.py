# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodeconductor_jira', '0003_add_issue_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='available_for_all',
            field=models.BooleanField(default=False, help_text=b'Allow access to any user'),
        ),
    ]
