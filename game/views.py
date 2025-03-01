import random

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Count
from django.http.response import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin

from game.models import Task, UserTask, CompletedTask


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

class AllPhotosView(LoginRequiredMixin, generic.ListView):
    model = UserTask
    template_name = "gallery.html"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().filter(
            completedtask__is_public=True
        ).select_related("user", "completedtask").order_by("-completedtask__date_completed")

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

