import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_role'),
        ('tenancies', '0002_tenancy_period'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='account',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tenant_record',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
