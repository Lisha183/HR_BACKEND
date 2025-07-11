# Generated by Django 5.2.3 on 2025-06-24 08:48

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_remove_selfassessment_employee_comments_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeetingSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(help_text='Date of the meeting slot.')),
                ('start_time', models.TimeField(help_text='Start time of the meeting slot.')),
                ('end_time', models.TimeField(help_text='End time of the meeting slot.')),
                ('is_booked', models.BooleanField(default=False, help_text='Indicates if the slot has been booked by an employee.')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the slot was created.')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp when the slot was last updated.')),
                ('booked_by_employee', models.ForeignKey(blank=True, help_text='The employee who booked this meeting slot (if booked).', limit_choices_to={'role': 'employee'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booked_meeting_slots', to=settings.AUTH_USER_MODEL)),
                ('hr_reviewer', models.ForeignKey(help_text='The HR/Admin user who scheduled this meeting slot.', limit_choices_to={'is_staff': True}, on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_meetings', to=settings.AUTH_USER_MODEL)),
                ('self_assessment', models.OneToOneField(blank=True, help_text='The self-assessment this meeting is for (optional).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='meeting_slot', to='myapp.selfassessment')),
            ],
            options={
                'verbose_name': 'Meeting Slot',
                'verbose_name_plural': 'Meeting Slots',
                'ordering': ['date', 'start_time'],
                'unique_together': {('hr_reviewer', 'date', 'start_time')},
            },
        ),
    ]
