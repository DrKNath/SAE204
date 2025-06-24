from django.shortcuts import render, get_object_or_404, redirect
from . import models
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from .forms import CapteurForm
import json
from datetime import datetime
from .bdd import MQTTToDatabaseProcessor, DB_CONFIG, MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD
import threading

# Pour éviter de lancer plusieurs threads simultanés
mqtt_thread = None
mqtt_processor = None

# Create your views here.
def index (request):
    return render(request,"Mesures/index.html")


def liste_mesures(request):
    # Récupérer tous les mesures par défaut
    mesures = models.Mesures.objects.all()
    
    # Récupérer les paramètres de filtre depuis l'URL
    filtre_emplacement = request.GET.get('emplacement', '')
    filtre_nom = request.GET.get('nom', '')
    filtre_temp_min = request.GET.get('temp_min', '')
    filtre_temp_max = request.GET.get('temp_max', '')
    filtre_date_debut = request.GET.get('date_debut', '')
    filtre_date_fin = request.GET.get('date_fin', '')
    
    # Appliquer les filtres si ils sont fournis
    if filtre_emplacement:
        mesures = mesures.filter(id_capteur__emplacement=filtre_emplacement)
    
    if filtre_nom:
        mesures = mesures.filter(id_capteur__nom_capteur=filtre_nom)
    
    # Filtre température minimum
    if filtre_temp_min:
        try:
            temp_min = float(filtre_temp_min)
            mesures = mesures.filter(temperature__gte=temp_min)
        except ValueError:
            pass
    
    # Filtre température maximum
    if filtre_temp_max:
        try:
            temp_max = float(filtre_temp_max)
            mesures = mesures.filter(temperature__lte=temp_max)
        except ValueError:
            pass
    
    # Filtre date début
    if filtre_date_debut:
        mesures = mesures.filter(timestamp__date__gte=filtre_date_debut)
    
    # Filtre date fin
    if filtre_date_fin:
        mesures = mesures.filter(timestamp__date__lte=filtre_date_fin)
    
    # Récupérer les valeurs uniques pour les listes déroulantes
    tous_noms = models.Mesures.objects.values_list('id_capteur__nom_capteur', flat=True).distinct().order_by('id_capteur__nom_capteur')
    tous_emplacements = models.Mesures.objects.values_list('id_capteur__emplacement', flat=True).distinct().order_by('id_capteur__emplacement')
    
    # Convertir en liste et passer au template
    mesures_list = list(mesures)

    # Préparer les données pour le graphique
    # Préparer les données pour le graphique, regroupées par capteur
    chart_labels = []
    chart_datasets = {} # Utiliser un dictionnaire pour stocker les données par capteur

    # Collecter toutes les timestamps uniques pour les labels de l'axe X
    all_timestamps = sorted(list(set([m.timestamp for m in mesures_list])))
    chart_labels = [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in all_timestamps]

    # Initialiser les datasets pour chaque capteur
    for nom_capteur in tous_noms: # tous_noms est déjà disponible
        chart_datasets[nom_capteur] = {
            'label': f'Température ({nom_capteur})',
            'data': [None] * len(chart_labels),
            'borderColor': f'hsl({hash(nom_capteur) % 360}, 70%, 50%)', # Couleur dynamique
            'tension': 0.1,
            'fill': False
        }

    # Remplir les données pour chaque capteur
    for mesure in mesures_list:
        capteur_nom = mesure.id_capteur.nom_capteur
        timestamp_str = mesure.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        try:
            index = chart_labels.index(timestamp_str)
            chart_datasets[capteur_nom]['data'][index] = float(mesure.temperature)
        except ValueError:
            pass

    final_chart_datasets = list(chart_datasets.values())

    context = {
        'mesures': mesures_list,
        'tous_noms': tous_noms,
        'tous_emplacements': tous_emplacements,
        'filtre_emplacement': filtre_emplacement,
        'filtre_nom': filtre_nom,
        'filtre_temp_min': filtre_temp_min,
        'filtre_temp_max': filtre_temp_max,
        'filtre_date_debut': filtre_date_debut,
        'filtre_date_fin': filtre_date_fin,
        'chart_labels': json.dumps(chart_labels), # Pass as JSON string
        'chart_datasets': json.dumps(final_chart_datasets),     # Pass as JSON string
    }
    
    return render(request, 'Mesures/liste_mesures.html', context)


# NOUVELLE VUE AJAX pour les mises à jour automatiques
def get_mesures_data(request):
    """
    Endpoint AJAX pour récupérer les données de mesures en JSON
    """
    # Récupérer tous les mesures par défaut
    mesures = models.Mesures.objects.all()
    
    # Récupérer les paramètres de filtre depuis l'URL
    filtre_emplacement = request.GET.get('emplacement', '')
    filtre_nom = request.GET.get('nom', '')
    filtre_temp_min = request.GET.get('temp_min', '')
    filtre_temp_max = request.GET.get('temp_max', '')
    filtre_date_debut = request.GET.get('date_debut', '')
    filtre_date_fin = request.GET.get('date_fin', '')
    
    # Appliquer les mêmes filtres que la vue principale
    if filtre_emplacement:
        mesures = mesures.filter(id_capteur__emplacement=filtre_emplacement)
    
    if filtre_nom:
        mesures = mesures.filter(id_capteur__nom_capteur=filtre_nom)
    
    if filtre_temp_min:
        try:
            temp_min = float(filtre_temp_min)
            mesures = mesures.filter(temperature__gte=temp_min)
        except ValueError:
            pass
    
    if filtre_temp_max:
        try:
            temp_max = float(filtre_temp_max)
            mesures = mesures.filter(temperature__lte=temp_max)
        except ValueError:
            pass
    
    if filtre_date_debut:
        mesures = mesures.filter(timestamp__date__gte=filtre_date_debut)
    
    if filtre_date_fin:
        mesures = mesures.filter(timestamp__date__lte=filtre_date_fin)
    
    # Récupérer les valeurs uniques pour les listes déroulantes
    tous_noms = models.Mesures.objects.values_list('id_capteur__nom_capteur', flat=True).distinct().order_by('id_capteur__nom_capteur')
    
    # Convertir en liste
    mesures_list = list(mesures.order_by('-timestamp'))  # Les plus récentes en premier
    
    # Préparer les données pour le tableau
    table_data = []
    for mesure in mesures_list:
        table_data.append({
            'nom_capteur': mesure.id_capteur.nom_capteur,
            'emplacement': mesure.id_capteur.emplacement,
            'temperature': float(mesure.temperature),
            'timestamp': mesure.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Préparer les données pour le graphique
    chart_labels = []
    chart_datasets = {}
    
    # Collecter toutes les timestamps uniques pour les labels de l'axe X
    all_timestamps = sorted(list(set([m.timestamp for m in mesures_list])))
    chart_labels = [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in all_timestamps]
    
    # Initialiser les datasets pour chaque capteur
    for nom_capteur in tous_noms:
        chart_datasets[nom_capteur] = {
            'label': f'Température ({nom_capteur})',
            'data': [None] * len(chart_labels),
            'borderColor': f'hsl({hash(nom_capteur) % 360}, 70%, 50%)',
            'tension': 0.1,
            'fill': False
        }
    
    # Remplir les données pour chaque capteur
    for mesure in mesures_list:
        capteur_nom = mesure.id_capteur.nom_capteur
        timestamp_str = mesure.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        try:
            index = chart_labels.index(timestamp_str)
            chart_datasets[capteur_nom]['data'][index] = float(mesure.temperature)
        except ValueError:
            pass
    
    final_chart_datasets = list(chart_datasets.values())
    
    # Retourner les données en JSON
    return JsonResponse({
        'table_data': table_data,
        'chart_labels': chart_labels,
        'chart_datasets': final_chart_datasets,
        'total_count': len(table_data)
    })


def export_mesures_json(request):
    """
    Exporte les mesures en fichier JSON téléchargeable
    """
    mesures = models.Mesures.objects.all()
    
    # Appliquer les mêmes filtres que les autres vues
    filtre_emplacement = request.GET.get('emplacement', '')
    filtre_nom = request.GET.get('nom', '')
    filtre_temp_min = request.GET.get('temp_min', '')
    filtre_temp_max = request.GET.get('temp_max', '')
    filtre_date_debut = request.GET.get('date_debut', '')
    filtre_date_fin = request.GET.get('date_fin', '')
    
    if filtre_emplacement:
        mesures = mesures.filter(id_capteur__emplacement=filtre_emplacement)
    
    if filtre_nom:
        mesures = mesures.filter(id_capteur__nom_capteur=filtre_nom)
    
    if filtre_temp_min:
        try:
            temp_min = float(filtre_temp_min)
            mesures = mesures.filter(temperature__gte=temp_min)
        except ValueError:
            pass
    
    if filtre_temp_max:
        try:
            temp_max = float(filtre_temp_max)
            mesures = mesures.filter(temperature__lte=temp_max)
        except ValueError:
            pass
    
    if filtre_date_debut:
        mesures = mesures.filter(timestamp__date__gte=filtre_date_debut)
    
    if filtre_date_fin:
        mesures = mesures.filter(timestamp__date__lte=filtre_date_fin)
    
    # Préparer les données d'exportation
    export_data = {
        'metadata': {
            'exported_at': datetime.now().isoformat(),
            'total_records': mesures.count(),
            'filters_applied': {
                'emplacement': filtre_emplacement if filtre_emplacement else None,
                'nom_capteur': filtre_nom if filtre_nom else None,
                'temperature_min': float(filtre_temp_min) if filtre_temp_min else None,
                'temperature_max': float(filtre_temp_max) if filtre_temp_max else None,
                'date_debut': filtre_date_debut if filtre_date_debut else None,
                'date_fin': filtre_date_fin if filtre_date_fin else None,
            }
        },
        'mesures': []
    }
    
    # Ajouter les mesures à l'export
    for mesure in mesures.order_by('-timestamp'):
        export_data['mesures'].append({
            'id_mesure': mesure.id_mesure,
            'capteur': {
                'id_capteur': mesure.id_capteur.id_capteur,
                'nom_capteur': mesure.id_capteur.nom_capteur,
                'emplacement': mesure.id_capteur.emplacement,
                'piece': mesure.id_capteur.piece if hasattr(mesure.id_capteur, 'piece') else None,
            },
            'temperature': float(mesure.temperature),
            'timestamp': mesure.timestamp.isoformat(),
            'timestamp_readable': mesure.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    # Créer la réponse HTTP avec le fichier JSON
    response = HttpResponse(
        json.dumps(export_data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    
    # Générer un nom de fichier avec la date et heure actuelles
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'mesures_export_{timestamp}.json'
    
    # Ajouter les en-têtes pour forcer le téléchargement
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(response.content)
    
    return response


def start_mqtt_collection(request):
    global mqtt_thread, mqtt_processor
    if mqtt_thread and mqtt_thread.is_alive():
        return JsonResponse({'status': 'Déjà en cours'})
    mqtt_config = {
        'broker': MQTT_BROKER,
        'port': MQTT_PORT,
        'topic': MQTT_TOPIC,
        'username': MQTT_USERNAME,
        'password': MQTT_PASSWORD,
    }
    mqtt_processor = MQTTToDatabaseProcessor(DB_CONFIG, mqtt_config)
    mqtt_thread = threading.Thread(target=mqtt_processor.start, daemon=True)
    mqtt_thread.start()
    return JsonResponse({'status': 'Collecte démarrée'})

def stop_mqtt_collection(request):
    global mqtt_processor
    if mqtt_processor:
        mqtt_processor.stop()
        return JsonResponse({'status': 'Collecte arrêtée'})
    return JsonResponse({'status': 'Aucune collecte en cours'})


def liste_capteurs(request):
    # Récupérer tous les capteurs
    capteurs = models.Capteur.objects.all()
    
    # Récupérer les paramètres de filtre depuis l'URL
    filtre_emplacement = request.GET.get('emplacement', '')
    filtre_nom = request.GET.get('nom', '')
    
    # Appliquer les filtres si ils sont fournis
    if filtre_emplacement:
        capteurs = capteurs.filter(emplacement=filtre_emplacement)
    
    if filtre_nom:
        capteurs = capteurs.filter(nom_capteur=filtre_nom)
    
    # Récupérer les valeurs uniques pour les listes déroulantes
    tous_noms = models.Capteur.objects.values_list('nom_capteur', flat=True).distinct().order_by('nom_capteur')
    tous_emplacements = models.Capteur.objects.values_list('emplacement', flat=True).distinct().order_by('emplacement')
    tous_pieces = models.Capteur.objects.values_list('piece', flat=True).distinct().order_by('piece')
    
    context = {
        'capteurs': capteurs,
        'tous_noms': tous_noms,
        'tous_emplacements': tous_emplacements,
        'tous_pieces': tous_pieces,
        'filtre_emplacement': filtre_emplacement,
        'filtre_nom': filtre_nom,
    }
    
    return render(request, 'mesures/liste_capteurs.html', context)

def modifier_capteur(request, id):
    try:
        capteur = models.Capteur.objects.get(id_capteur=id)
    except models.Capteur.DoesNotExist:
        return HttpResponseRedirect('liste_mesures')  # ou erreur personnalisée

    if request.method == 'POST':
        form = CapteurForm(request.POST, instance=capteur)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/Mesures/liste_capteurs/")  # Rediriger vers la liste des capteurs
    else:
        form = CapteurForm(instance=capteur)

    return render(request, 'mesures/modifier_capteur.html', {'form': form})