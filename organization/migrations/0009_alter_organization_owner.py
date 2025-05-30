# Generated by Django 5.2 on 2025-05-13 15:13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0008_alter_organization_owner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='org_owner', to=settings.AUTH_USER_MODEL, verbose_name='organization owner'),
        ),
    ]
