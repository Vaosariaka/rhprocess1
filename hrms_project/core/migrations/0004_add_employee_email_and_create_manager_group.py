# Generated manually: add email field to Employee and create Manager group
from django.db import migrations, models


def create_manager_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Manager')


def delete_manager_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    try:
        g = Group.objects.get(name='Manager')
        g.delete()
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_contract_sector_presence_holiday_minutes_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(create_manager_group, reverse_code=delete_manager_group),
    ]
