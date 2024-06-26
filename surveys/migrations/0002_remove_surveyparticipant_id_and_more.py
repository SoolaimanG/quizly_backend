# Generated by Django 5.0.4 on 2024-04-24 07:54

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='surveyparticipant',
            name='id',
        ),
        migrations.AlterField(
            model_name='surveyparticipant',
            name='user_id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='userreponse',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
    ]
