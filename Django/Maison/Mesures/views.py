from django.shortcuts import render, get_object_or_404, redirect
from . import models
from django.http import HttpResponseRedirect
from .forms import CapteurForm

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
    }
    
    return render(request, 'Mesures/liste_mesures.html', context)


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
            return HttpResponseRedirect('liste_mesures')
    else:
        form = CapteurForm(instance=capteur)

    return render(request, 'mesures/modifier_capteur.html', {'form': form})

