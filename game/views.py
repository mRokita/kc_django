from django import forms
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from game.models import Task


class SignUpForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "password"]

@csrf_exempt
def signup(request: HttpRequest, req_id: int) -> HttpResponse:
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save(commit=True)
        return HttpResponse(f"Siema! {req_id}")
    else:
        return HttpResponse(f"<form method='post'>{form}<button type='submit'>zarejestruj</button></form>")