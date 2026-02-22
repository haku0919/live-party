import django.core.validators
from django.db import migrations, models


def normalize_legacy_phone_numbers(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    def make_fallback(seed, used):
        candidate_seed = max(int(seed or 1), 1)
        while True:
            candidate = f"9{candidate_seed:010d}"[-11:]
            if candidate not in used:
                return candidate
            candidate_seed += 1

    used_numbers = set()

    for user in User.objects.order_by("id").only("id", "phone").iterator():
        raw_phone = user.phone or ""
        digits = "".join(ch for ch in raw_phone if ch.isdigit())

        normalized = None
        if len(digits) == 11 and digits not in used_numbers:
            normalized = digits
        elif len(digits) > 11:
            last_11 = digits[-11:]
            if last_11 not in used_numbers:
                normalized = last_11

        if normalized is None:
            normalized = make_fallback(user.id, used_numbers)

        if normalized != raw_phone:
            User.objects.filter(pk=user.pk).update(phone=normalized)
        used_numbers.add(normalized)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_user_birth_year'),
    ]

    operations = [
        migrations.RunPython(normalize_legacy_phone_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='전화번호는 숫자 11자리여야 합니다.', regex='^\\d{11}$')]),
        ),
    ]
