from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("<slug:slug>/new/", views.submit_review, name="submit"),
    path("<int:pk>/delete/", views.delete_review, name="delete"),
]
