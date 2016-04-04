# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('nodeconductor_jira', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jiraserviceprojectlink',
            name='error_message',
        ),
        migrations.RemoveField(
            model_name='jiraserviceprojectlink',
            name='state',
        ),
        migrations.AddField(
            model_name='issue',
            name='resolution',
            field=models.CharField(default='', blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='issue',
            name='status',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='issue',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
