# Generated by Django 5.1.3 on 2024-12-11 22:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twigaapp', '0005_rename_paid_bookings_mpesarequestsent'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bookings',
            old_name='bookingType',
            new_name='type',
        ),
    ]
