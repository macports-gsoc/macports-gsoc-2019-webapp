# Generated by Django 2.2.10 on 2020-07-12 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('port', '0006_port_subscribers'),
    ]

    operations = [
        migrations.AddField(
            model_name='port',
            name='version_updated_at',
            field=models.DateTimeField(null=True),
        ),
    ]
