# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-01-30 16:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0009_auto_20180124_2138'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='legalentity',
            unique_together=set([]),
        ),
        migrations.AlterUniqueTogether(
            name='location',
            unique_together=set([]),
        ),
    ]
