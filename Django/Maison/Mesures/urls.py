from django.urls import path
from . import views

urlpatterns = [
        path("", views.index, name="index"),
        path("liste_mesures/", views.liste_mesures, name="liste_mesures"),
        path("modifier_capteur/<str:id>/", views.modifier_capteur, name="modifier_capteur"),
        path("liste_capteurs/", views.liste_capteurs, name="liste_capteurs"),
]