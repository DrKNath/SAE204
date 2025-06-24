from django.urls import path
from . import views

urlpatterns = [
        path("", views.index, name="index"),
        path("liste_mesures/", views.liste_mesures, name="liste_mesures"),
        path("modifier_capteur/<str:id>/", views.modifier_capteur, name="modifier_capteur"),
        path("liste_capteurs/", views.liste_capteurs, name="liste_capteurs"),
        path("export/json/", views.export_mesures_json, name='export_mesures_json'),
        path("start-mqtt/", views.start_mqtt_collection, name='start_mqtt'),
        path("stop-mqtt/", views.stop_mqtt_collection, name='stop_mqtt'),
        path("api/mesures-data/", views.get_mesures_data, name='get_mesures_data'),
]