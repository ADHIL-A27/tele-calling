from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_groups(sender, **kwargs):
    from django.contrib.auth.models import Group

    from apps.accounts.models import ROLE_GROUP_NAMES

    for group_name in ROLE_GROUP_NAMES.values():
        Group.objects.get_or_create(name=group_name)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        post_migrate.connect(create_default_groups, sender=self)
