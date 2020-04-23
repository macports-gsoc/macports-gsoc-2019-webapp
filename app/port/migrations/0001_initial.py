# Generated by Django 2.2.10 on 2020-04-23 18:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('category', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LastPortIndexUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('git_commit_hash', models.CharField(max_length=50, verbose_name='Commit hash till which update was done')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Timestamp when update completed')),
            ],
            options={
                'verbose_name': 'PortIndex Update',
                'verbose_name_plural': 'PortIndex Updates',
                'db_table': 'portindex_update',
            },
        ),
        migrations.CreateModel(
            name='Port',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('portdir', models.CharField(max_length=100)),
                ('description', models.TextField(default='')),
                ('homepage', models.URLField(default='')),
                ('epoch', models.BigIntegerField(default=0)),
                ('platforms', models.TextField(null=True)),
                ('long_description', models.TextField(default='')),
                ('version', models.CharField(default='', max_length=100)),
                ('revision', models.IntegerField(default=0)),
                ('closedmaintainer', models.BooleanField(default=False)),
                ('name', models.CharField(db_index=True, max_length=100)),
                ('license', models.CharField(default='', max_length=100)),
                ('replaced_by', models.CharField(max_length=100, null=True)),
                ('active', models.BooleanField(default=True)),
                ('categories', models.ManyToManyField(db_index=True, related_name='ports', to='category.Category')),
            ],
            options={
                'verbose_name': 'Port',
                'verbose_name_plural': 'Ports',
                'db_table': 'port',
            },
        ),
        migrations.CreateModel(
            name='Dependency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=100)),
                ('dependencies', models.ManyToManyField(to='port.Port')),
                ('port_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dependent_port', to='port.Port')),
            ],
            options={
                'verbose_name': 'Dependency',
                'verbose_name_plural': 'Dependencies',
                'db_table': 'dependency',
            },
        ),
        migrations.AddIndex(
            model_name='dependency',
            index=models.Index(fields=['port_name'], name='dependency_port_na_a6e0f8_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='dependency',
            unique_together={('port_name', 'type')},
        ),
    ]
