from django.db import models


class Layer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, help_text='Nome da camada que cont\u00E9m um ou mais pontos de controle')
    
    def __str__(self):
        return self.name


class ControlPoint(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, help_text='Nome do ponto de controle cont\u00E9m uma ou mais c\u00E2meras')
    address = models.CharField(max_length=200, help_text='Endere\u00E7o de localiza\u00E7\u00E3o do ponto de controle')
    latitude = models.FloatField(help_text='Latitude da localiza\u00E7\u00E3o do ponto de controle')
    longitude = models.FloatField(help_text='Longitude da localiza\u00E7\u00E3o do ponto de controle')
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, help_text='Camada a qual o ponto de controle pertence')
    
    def __str__(self):
        return self.name


class Camera(models.Model):
    DIRECTIONS = (
        ('in', 'Entrada do munic\u00EDpio'),
        ('out', 'Sa\u00EDda do munic\u00EDpio'),
        ('even', 'Lado par da via'),
        ('odd', 'Lado \u00EDmpar da via'),
        ('free', 'Movimento livre (domo)'),
        ('sidewalk', 'C\u00E2mera de cal\u00E7ada')
    )
    
    id = models.AutoField(primary_key=True)
    tag_slug = models.SlugField(max_length=50, unique=True, help_text='Mnem\u00F4nico identificador da c\u00E2mera. Deve ser \u00FAnico e conter apenas letras, n\u00FAmeros, sublinhados e h\u00EDfens')
    direction = models.CharField(max_length=8, choices=DIRECTIONS, help_text='Dire\u00E7\u00E3o para a qual a c\u00E2mera est\u00E1 apontada')
    model = models.CharField(max_length=200, help_text='Modelo da c\u00E2mera')
    rtsp_url = models.URLField(max_length=200, unique=True, help_text='URL do fluxo de v\u00EDdeo, conforme definido no Real Time Streaming Protocol (RTSP)')
    agent_user = models.CharField(max_length=100, help_text='Nome do usu\u00E1rio com acesso \u00E0 m\u00E1quina onde o agente \u00E9 executado')
    agent_server = models.GenericIPAddressField(max_length=200, help_text='Endere\u00E7o IP da m\u00E1quina onde o agente \u00E9 executado')
    controlpoint = models.ForeignKey(ControlPoint, on_delete=models.CASCADE, help_text='Ponto de controle ao qual a c\u00E2mera pertence')
        
    def direction_verbose(self):
        return dict(Camera.DIRECTIONS)[self.direction]
        
    def __str__(self):
        return self.tag_slug


class DetectedLicensePlate(models.Model):
    id = models.AutoField(primary_key=True)
    detection_date = models.DateTimeField(help_text='Data e hora da detec\u00E7\u00E3o')
    license_plate = models.CharField(max_length=7, help_text='Placa de carro identificada a partir da(s) imagem(s)')
    data_filename = models.CharField(max_length=256, help_text='Nome do arquivo ZIP que cont\u00E9m a(s) imagem(s) utilizada(s) na identifica\u00E7\u00E3o da placa do carro')
    data_password = models.CharField(max_length=8, help_text='Senha utilizada na compress\u00E3o do arquivo ZIP que cont\u00E9m a(s) imagem(s) utilizada(s) na identifica\u00E7\u00E3o da placa do carro')
    data_md5 = models.CharField(max_length=32, help_text='Valor de verifica\u00E7\u00E3o calculado conforme o algor\u00EDtimo MD5 sobre o arquivo ZIP que cont\u00E9m a(s) imagen(s) utilizada(s) na identifica\u00E7\u00E3o da placa do carro')
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, help_text='C\u00E2mera de origem da(s) imagem(s) registrada(s)')
