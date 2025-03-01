from django.db import models
from django.utils.translation import gettext_lazy as _

class Task(models.Model):
    description: str = models.TextField(
        verbose_name=_("Task description")
    )

    def __str__(self) -> str:
        return self.description
