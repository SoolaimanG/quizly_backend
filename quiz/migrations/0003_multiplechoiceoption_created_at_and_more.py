# Generated by Django 5.0.4 on 2024-05-04 01:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0002_remove_anonymoususer_ip_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='multiplechoiceoption',
            name='created_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='multiplechoiceoption',
            name='updated_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
