# Generated by Django 5.2 on 2025-05-07 12:12

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0002_rename_last_modified_organization_updated_at_and_more'),
        ('user', '0006_alter_appuser_email_alter_appuser_orgs'),
    ]

    operations = [
        migrations.AddField(
            model_name='appuser',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Créateur'),
        ),
        migrations.AlterField(
            model_name='appuser',
            name='orgs',
            field=models.ManyToManyField(blank=True, to='organization.organization', verbose_name='organizations'),
        ),
    ]
