# Generated by Django 2.2.10 on 2020-04-17 15:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Builder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=100)),
                ('display_name', models.CharField(db_index=True, default='', max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='BuildHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('build_id', models.IntegerField()),
                ('status', models.CharField(max_length=50)),
                ('port_name', models.CharField(max_length=100)),
                ('time_start', models.DateTimeField()),
                ('time_elapsed', models.DurationField(null=True)),
                ('watcher_id', models.IntegerField()),
                ('builder_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='builds.Builder')),
            ],
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['port_name', 'builder_name', '-build_id'], name='builds_buil_port_na_98faf1_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['port_name', 'builder_name', '-time_start'], name='builds_buil_port_na_e743c2_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['port_name', 'status', 'builder_name'], name='builds_buil_port_na_1b3b5c_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['port_name', 'builder_name'], name='builds_buil_port_na_cc230e_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['-time_start'], name='builds_buil_time_st_74d76d_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['port_name'], name='builds_buil_port_na_65b879_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['status'], name='builds_buil_status_abcc89_idx'),
        ),
        migrations.AddIndex(
            model_name='buildhistory',
            index=models.Index(fields=['builder_name'], name='builds_buil_builder_1224f1_idx'),
        ),
    ]
