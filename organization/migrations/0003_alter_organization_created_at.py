# Generated by Django 5.2 on 2025-05-07 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0002_rename_last_modified_organization_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
    ]
