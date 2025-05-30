# Generated by Django 5.2 on 2025-05-13 15:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0006_remove_organization_departments'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='owner',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='org_owner', to=settings.AUTH_USER_MODEL, verbose_name='organization owner'),
        ),
    ]
