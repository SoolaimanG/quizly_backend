# Generated by Django 5.0.4 on 2024-05-01 00:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communities', '0001_initial'),
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posts',
            name='quiz',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='quiz.quiz'),
        ),
    ]