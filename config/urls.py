from django.urls import path
from booking import views

urlpatterns = [
    path("", views.index, name="index"),
    path("reserve/", views.reserve, name="reserve"),
    path("cancel/<uuid:reference>/", views.cancel, name="cancel"),
    path("health/", views.health, name="health"),
]
