from django.db import models


class Capteur(models.Model):
    id_capteur = models.CharField(primary_key=True, max_length=20)
    nom_capteur = models.CharField(unique=True, max_length=50)
    piece = models.CharField(max_length=50)
    emplacement = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'capteur'

    def __str__(self):
        return f"{self.nom_capteur} ({self.piece})"



class Mesures(models.Model):
    id_mesure = models.AutoField(primary_key=True)
    id_capteur = models.ForeignKey(Capteur, models.DO_NOTHING, db_column='id_capteur', blank=True, null=True)
    timestamp = models.DateTimeField()
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mesures'

    def __str__(self):
        return f"Mesure {self.id_mesure} - Capteur: {self.id_capteur.nom_capteur if self.id_capteur else 'N/A'} - Temp: {self.temperature}°C - Time: {self.timestamp}"