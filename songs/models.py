from django.db import models
from django.conf import settings

class Songs(models.Model):
    url = models.URLField()
    titulo = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)

class Vote(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    songs = models.ForeignKey(Songs, related_name='votes', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)

    class Meta:
        unique_together = ('user', 'songs') 


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Songs, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
