from django.urls import path

from . import views

app_name = "destinations"

urlpatterns = [
    path("destinations/", views.DestinationListView.as_view(), name="destination_list"),
    path(
        "destinations/<slug:slug>/",
        views.DestinationDetailView.as_view(),
        name="destination_detail",
    ),
    path("trips/", views.PackageListView.as_view(), name="package_list"),
    path("trips/<slug:slug>/", views.PackageDetailView.as_view(), name="package_detail"),
]
