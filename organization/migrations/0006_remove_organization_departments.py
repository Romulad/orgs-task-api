# Generated by Django 5.2 on 2025-05-13 14:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0005_organization_departments_alter_organization_members'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='departments',
        ),
    ]
