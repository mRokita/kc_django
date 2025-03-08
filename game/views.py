import json
import random
import logging

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Count, Prefetch
from django.http.response import HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin
from django.contrib.auth.decorators import login_required

from game.models import Task, UserTask, CompletedTask, EMOJI_CHOICES, EmojiReaction


class SignUpView(generic.CreateView):
    template_name = "registration/signup.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("login")


class TaskListView(LoginRequiredMixin, generic.ListView):
    model = UserTask
    template_name = "tasks.html"

    def get_queryset(self):
        return super().get_queryset().filter(
            user=self.request.user,
            completedtask=None).order_by("-id")

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx["completed_tasks"] = super().get_queryset().filter(
            user=self.request.user
        ).exclude(completedtask=None)
        return ctx

class CompletedTaskForm(forms.ModelForm):
    class Meta:
        model = CompletedTask
        fields = ["photo", "is_public"]

class MyPhotosView(LoginRequiredMixin, generic.ListView):
    model = UserTask
    template_name = "gallery.html"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().filter(
            user=self.request.user
        ).order_by("-completedtask__date_completed").exclude(completedtask=None).select_related("user", "completedtask")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        completed_tasks = self.get_queryset().filter(completedtask__is_public=True)

        # Add emoji stats for each completed task
        for task in completed_tasks:
            reactions = (
                EmojiReaction.objects
                .filter(completed_task=task.completedtask)
                .values('emoji')
                .annotate(count=Count('emoji'))
            )

            # Tworzymy słownik {emoji: liczba}, aby uniknąć problemów z pustą listą
            task.emoji_stats = {reaction["emoji"]: reaction["count"] for reaction in reactions} if reactions else {}

            # Pobieramy reakcję użytkownika, jeśli istnieje
            user_reaction = EmojiReaction.objects.filter(user=self.request.user,
                                                         completed_task=task.completedtask).first()
            task.user_reacted_emoji = user_reaction.emoji if user_reaction else None

        ctx["page_obj"] = completed_tasks
        ctx["EMOJI_CHOICES"] = EMOJI_CHOICES
        return ctx

class AllPhotosView(LoginRequiredMixin, generic.ListView):
    model = UserTask
    template_name = "gallery.html"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().filter(
            completedtask__is_public=True
        ).select_related("user", "completedtask").order_by("-completedtask__date_completed")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        completed_tasks = self.get_queryset().filter(completedtask__is_public=True)

        # Add emoji stats for each completed task
        for task in completed_tasks:
            reactions = (
                EmojiReaction.objects
                .filter(completed_task=task.completedtask)
                .values('emoji')
                .annotate(count=Count('emoji'))
            )

            # Tworzymy słownik {emoji: liczba}, aby uniknąć problemów z pustą listą
            task.emoji_stats = {reaction["emoji"]: reaction["count"] for reaction in reactions} if reactions else {}

            # Pobieramy reakcję użytkownika, jeśli istnieje
            user_reaction = EmojiReaction.objects.filter(user=self.request.user,
                                                         completed_task=task.completedtask).first()
            task.user_reacted_emoji = user_reaction.emoji if user_reaction else None

        ctx["page_obj"] = completed_tasks
        ctx["EMOJI_CHOICES"] = EMOJI_CHOICES
        return ctx


class TaskDetailView(LoginRequiredMixin, FormMixin, generic.DetailView):
    model = UserTask
    form_class = CompletedTaskForm
    template_name = "task_detail.html"
    success_url = reverse_lazy("tasks")

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            return redirect(reverse("tasks"))

    def get_queryset(self):
        return self.request.user.usertask_set.filter(completedtask=None)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            completed_task = form.save(commit=False)
            completed_task.user = self.request.user
            completed_task.user_task = self.object
            completed_task.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leaderboard"] = CompletedTask.objects.filter(task_verified=True).select_related(
            "usertask").annotate(
            username=F("user_task__user__username")).values("username").annotate(
            count=Count("id")
        ).filter(count__gt=0).order_by("-count")[:3]
        return ctx


    @transaction.atomic
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        user: User = self.request.user  # type: ignore[assignment]
        if user.usertask_set.filter(completedtask=None).count() > 4:
            context["draw_error"] = _("User already has 5 incomplete tasks")
        else:
            task_ids = Task.objects.exclude(usertask__user=user).values_list(
                "id", flat=True)
            if task_ids:
                task_id = random.choice(task_ids)
                task = Task.objects.get(id=task_id)
                UserTask(user=user, task=task).save()
                return HttpResponseRedirect(reverse_lazy("tasks"))
            else:
                context["draw_error"] = _("There are no more tasks available.")
        return self.render_to_response(context)


class IndexView(TemplateView):
    template_name = "index.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy("dashboard"))
        return super().get(request, *args, **kwargs)


@login_required
@require_POST
def add_emoji_reaction(request, task_id, source):
    completed_task = get_object_or_404(CompletedTask, id=task_id)

    # Odczytaj dane JSON z ciała żądania
    try:
        data = json.loads(request.body)
        emoji = data.get('emoji')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})

    if not emoji:
        return JsonResponse({'success': False, 'error': 'No emoji received'})

    existing_reaction = EmojiReaction.objects.filter(
        user=request.user,
        completed_task=completed_task
    ).first()

    if existing_reaction:
        if existing_reaction.emoji != emoji:
            existing_reaction.emoji = emoji
            existing_reaction.save()
    else:
        EmojiReaction.objects.create(
            user=request.user,
            completed_task=completed_task,
            emoji=emoji
        )

    stats = EmojiReaction.get_reaction_stats(completed_task)
    return JsonResponse({
        'success': True,
        'stats': list(stats),
    })

# Default redirection

@login_required
@require_POST
def delete_emoji_reaction(request, task_id):
    completed_task = get_object_or_404(CompletedTask, id=task_id)
    EmojiReaction.delete_reaction(request.user, completed_task)

    # Fetch updated reaction stats
    stats = EmojiReaction.get_reaction_stats(completed_task)
    return JsonResponse({
        'success': True,
        'stats': list(stats),
    })

