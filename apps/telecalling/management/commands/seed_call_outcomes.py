from django.core.management.base import BaseCommand

from apps.telecalling.models import DEFAULT_CALL_OUTCOMES, CallOutcome


class Command(BaseCommand):
    help = "Seed the default set of admin-manageable call outcomes."

    def handle(self, *args, **options):
        created = 0
        for order, (name, slug, category, requires_follow_up) in enumerate(DEFAULT_CALL_OUTCOMES):
            _, was_created = CallOutcome.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "requires_follow_up": requires_follow_up,
                    "display_order": order,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded call outcomes. {created} newly created."))
