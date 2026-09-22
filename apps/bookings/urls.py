from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingListView.as_view(), name="list"),
    path("checkout/<slug:slug>/", views.checkout, name="checkout"),
    path("quote/<slug:slug>/", views.price_quote, name="quote"),
    path("<str:reference>/pay/", views.pay, name="pay"),
    path("<str:reference>/callback/", views.payment_callback, name="callback"),
    path("<str:reference>/confirmed/", views.BookingConfirmationView.as_view(), name="confirmation"),
    path("<str:reference>/cancel/", views.cancel_booking, name="cancel"),
    path("<str:reference>/", views.BookingDetailView.as_view(), name="detail"),
]
