from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("match_requests", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE match_requests
                    ADD COLUMN IF NOT EXISTS visibility_scope VARCHAR(30) NOT NULL DEFAULT 'only_this_user';
                ALTER TABLE match_requests
                    ADD COLUMN IF NOT EXISTS note TEXT;
            """,
            reverse_sql="""
                ALTER TABLE match_requests DROP COLUMN IF EXISTS visibility_scope;
                ALTER TABLE match_requests DROP COLUMN IF EXISTS note;
            """,
        ),
    ]
