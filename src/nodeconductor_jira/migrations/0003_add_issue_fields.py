# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc
import django.utils.timezone
from django.conf import settings
import django_fsm
import uuidfield.fields
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('nodeconductor_jira', '0002_more_issue_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('uuid', uuidfield.fields.UUIDField(unique=True, max_length=32, editable=False, blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('state', django_fsm.FSMIntegerField(default=5, choices=[(5, 'Creation Scheduled'), (6, 'Creating'), (1, 'Update Scheduled'), (2, 'Updating'), (7, 'Deletion Scheduled'), (8, 'Deleting'), (3, 'OK'), (4, 'Erred')])),
                ('file', models.FileField(upload_to=b'jira_attachments')),
                ('backend_id', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='issue',
            name='impact',
            field=models.SmallIntegerField(default=0, choices=[(0, b'n/a'), (1, b'Small - Partial loss of service, one person affected'), (2, b'Medium - One department or service is affected'), (3, b'Large - Whole organization or all services are affected')]),
        ),
        migrations.AddField(
            model_name='issue',
            name='priority',
            field=models.SmallIntegerField(default=0, choices=[(0, b'n/a'), (1, b'Minor'), (2, b'Major'), (3, b'Critical')]),
        ),
        migrations.AddField(
            model_name='issue',
            name='type',
            field=models.CharField(default='Support Request', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='issue',
            name='updated',
            field=models.DateTimeField(default=datetime.datetime(2016, 4, 14, 17, 9, 18, 260377, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='issue',
            name='updated_username',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='impact_field',
            field=models.CharField(max_length=64, blank=True),
        ),
        migrations.AddField(
            model_name='attachment',
            name='issue',
            field=models.ForeignKey(related_name='attachments', to='nodeconductor_jira.Issue'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
