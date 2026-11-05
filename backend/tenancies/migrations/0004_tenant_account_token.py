from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancies', '0003_tenant_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='account_token_hash',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name='tenant',
            name='account_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
