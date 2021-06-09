from django import forms
from .models import Layer, ControlPoint, Camera, DetectedLicensePlate

class LayerForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ('name',)


class ControlpointForm(forms.ModelForm):
    class Meta:
        model = ControlPoint
        fields = ('name', 'address', 'latitude', 'longitude', 'layer')

class CameraForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ('tag_slug', 'direction', 'model', 'rtsp_url', 'agent_user', 'agent_server', 'controlpoint')