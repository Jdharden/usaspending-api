# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-20 17:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0005_auto_20160920_1732'),
    ]

    operations = [
        migrations.RenameField(
            model_name='agency',
            old_name='agency_id',
            new_name='cgac_code',
        ),
        migrations.RenameField(
            model_name='agency',
            old_name='agency_code_fpds',
            new_name='fpds_code',
        ),
        migrations.RenameField(
            model_name='agency',
            old_name='agency_name',
            new_name='name',
        ),
    ]
