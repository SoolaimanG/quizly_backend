# Generated by Django 5.0.4 on 2024-05-06 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0004_alter_attemptedquizbyanonymoususer_questions_attempted'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportsonquiz',
            name='created_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]