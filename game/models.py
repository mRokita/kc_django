from django.contrib.auth.models import User
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class UserTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey("Task", on_delete=models.CASCADE)

class CompletedTask(models.Model):
    task_verified = models.BooleanField(default=False)
    date_completed = models.DateTimeField(auto_now_add=True)
    user_task = models.OneToOneField(UserTask, on_delete=models.CASCADE)
    is_public = models.BooleanField(verbose_name=_("Opublikuj w galerii"), default=True)
    photo = models.ImageField(verbose_name=_("Photo"),
                              upload_to="tasks_photos/")

    def photo_tag(self):
        return mark_safe(f'<img src="{self.photo.url}" width="200" height="200" />')


class Task(models.Model):
    description: str = models.TextField(
        verbose_name=_("Task description")
    )
    users = models.ManyToManyField(to=User, through="UserTask")

    def __str__(self) -> str:
        return self.description

    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")