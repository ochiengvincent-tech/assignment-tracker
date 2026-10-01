from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("users", "UserProfile")
    database = schema_editor.connection.alias

    for user in User.objects.using(database).iterator():
        UserProfile.objects.using(database).get_or_create(
            user_id=user.pk,
            defaults={"role": "student"},
        )


class Migration(migrations.Migration):
    dependencies = [("users", "0001_initial")]

    operations = [migrations.RunPython(create_missing_profiles, migrations.RunPython.noop)]
