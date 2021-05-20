from django.contrib import admin

from .models import Layer, ControlPoint, Camera, DetectedLicensePlate

admin.site.register(Layer)
admin.site.register(ControlPoint)
admin.site.register(Camera)
admin.site.register(DetectedLicensePlate)