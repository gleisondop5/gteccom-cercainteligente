# Generated by Django 2.0.7 on 2018-07-20 00:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camera',
            name='agent_password',
        ),
    ]
