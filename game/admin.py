from django.contrib import admin

from game.models import Task, CompletedTask, UserTask


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "description")

@admin.register(CompletedTask)
class CompletedTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "user_task__user__username", "user_task__task__description")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user_task", "user_task__user", "user_task__task")

@admin.register(UserTask)
class UserTask(admin.ModelAdmin):
    list_display = ("id", "user", "task__description")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("task")

