# Generated by Django 5.1.3 on 2025-05-31 03:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0002_alter_room_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='code',
            field=models.CharField(default='bb23effb', max_length=8, unique=True),
        ),
    ]
