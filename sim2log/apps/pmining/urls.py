from django.urls import path

from sim2log.apps.pmining.views import pmining

urlpatterns = [
    path('', pmining.index, name='uploadxes'),
]