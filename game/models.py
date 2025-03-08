from django.contrib.auth.models import User
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

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

    def emoji_stats(self):
        return EmojiReaction.get_reaction_stats(self)


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

class EmojiReaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed_task = models.ForeignKey(CompletedTask, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10, verbose_name=_("Emoji"))

    class Meta:
        verbose_name = _("emoji reaction")
        verbose_name_plural = _("emoji reactions")
        unique_together = ('user', 'completed_task')  # Zapobiega wielokrotnym reakcjom od tego samego użytkownika

    def __str__(self):
        return f"{self.user.username} reacted with {self.emoji}"

    @staticmethod
    def delete_reaction(user, completed_task):
        """Usuwa reakcję użytkownika dla danego zadania."""
        EmojiReaction.objects.filter(user=user, completed_task=completed_task).delete()

    @staticmethod
    def get_reaction_stats(completed_task):
        """Zwraca statystyki reakcji dla danego zadania."""
        return EmojiReaction.objects.filter(completed_task=completed_task).values('emoji').annotate(count=Count('emoji')).order_by('-count')

EMOJI_CHOICES = [
    "💀", "❤️", "😂", "🤮", "🔥", "👀", "💩"
]