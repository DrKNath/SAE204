from django import forms
from .models import Capteur


class CapteurForm(forms.ModelForm):
    class Meta:
        model = Capteur
        fields = ['nom_capteur', 'emplacement']


