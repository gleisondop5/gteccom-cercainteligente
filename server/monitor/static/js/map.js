var map;
var bounds;
var socket;
var id = makeUUID();

function startAgent(tag_slug) {
    var camera = cameras.get(tag_slug);
    if (camera != undefined) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "agent/" + tag_slug + "/start/", true);
        xhr.send();
    }
}

function stopAgent(tag_slug) {
    var camera = cameras.get(tag_slug);
    if (camera != undefined) {
        var answer = confirm("Voc\xEA deseja desativar o agente da c\xE2mera " + (camera.controlpoint.cameras.indexOf(camera) + 1) + " do ponto de controle '" + camera.controlpoint.name + "'?");
        if (answer) {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "agent/" + tag_slug + "/stop/", true);
            xhr.send();
        }
    }
}

function askAgentProcessinRate(tag_slug) {
    var camera = cameras.get(tag_slug);
    if (camera != undefined) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "agent/" + tag_slug + "/ask-processing-rate/" + id, true);
        xhr.send();
    }
}

function openRTSPWindow(controlpoint_id) {
    window.open("rtsp-panel/" + controlpoint_id + "/" + id, "rtsp-panel", "toolbar=0,fullscreen=0,menubar=0,location=0");
}

function controlpointInfoContent(controlpoint) {
    var content = "<div>" +
        "<div><b>" + controlpoint.name + "</b><br>" + controlpoint.address + "</div>" +
        "<div>" +
        "<p>Latitude: " + controlpoint.latitude + "<br>Longitude: " + controlpoint.longitude + "</p>" +
        "<p><i>Agente(s)</i>";

    if (controlpoint.cameras.length != 0) {
        $.each(controlpoint.cameras, function(index, camera) {
            content += "<br>&ensp;" + (index + 1) + ". " + camera.direction;
            content += " <img src='" + ICONS.status[camera.status].icon + "' width='16' height='16'>";
            switch (camera.status) {
                case STATUS_AGENT_ON_CAMERA_OFF:
                case STATUS_AGENT_ON_CAMERA_ON:
                    content += " <a href=\"javascript:stopAgent('" + camera.tag_slug + "')\">desativar</a>";
                    content += " (<a href=\"javascript:askAgentProcessinRate('" + camera.tag_slug + "')\">fps</a>)";
                    break;
                case STATUS_AGENT_OFF:
                    content += " <a href=\"javascript:startAgent('" + camera.tag_slug + "')\">ativar</a>";
                    break;
            }
        });
        content += "</p><button onclick=\"openRTSPWindow(" + controlpoint.id + ")\">Abrir painel</button>";    
    }
    else {
        content += "<br>Nenhum agente cadastrado</p>";
    }

    content += "</div></div>";    
    
    return content;
}

function updateControlPoint(controlpoint) {
    var status = STATUS_UNKNOWN
    $.each(controlpoint.cameras, function(_, camera) {
        status = Math.min(status, camera.status);
    });
    controlpoint.marker.setIcon(ICONS.status[status].icon);
    controlpoint.marker.info.setContent(controlpointInfoContent(controlpoint));
}

function initMap() {
    map = new google.maps.Map(document.getElementById("map-canvas"), {
        center: new google.maps.LatLng(-22.5138892, -44.0937475),
        zoom: 13,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        mapTypeControl: false,
        streetViewControl: false
    });
    
    bounds = new google.maps.LatLngBounds();
    
    $.getJSON("../static/data/city.json", function(data) {
        $.each(data["city"].polygons, function(_, path) {
            var polygon = new google.maps.Polygon({
                paths: path,
                strokeColor: '#87CEEB',
                strokeOpacity: 1.00,
                strokeWeight: 1,
                fillColor: '#9BE2FF',
                fillOpacity: 0.20,
                map: map
            });
        });
    });
    
    for (var [_, controlpoint] of controlpoints) {
        var marker = new google.maps.Marker({
            title: controlpoint.name,
            position: new google.maps.LatLng(controlpoint.latitude, controlpoint.longitude),
            icon: ICONS.status[controlpoint.cameras.length == 0 ? STATUS_UNKNOWN : STATUS_AGENT_OFF].icon,
            info: new google.maps.InfoWindow({content: controlpointInfoContent(controlpoint), maxWidth: 350}),
            map: map,
        });
        
        marker.addListener("click", function() {
            this.info.open(map, this);
        });
        
        controlpoint.marker = marker;
        
        bounds.extend(marker.position);
    }
    
    map.fitBounds(bounds);
    
    socket = new WebSocket("ws://" + window.location.host + "/monitor/?group=monitor&name=" + id);
    
    socket.onmessage = function(event) {
        var data = JSON.parse(event.data);
        switch (data.type) {
            case "agent-connect":
            case "agent-update":
                var camera = cameras.get(data.who); 
                if (camera != undefined) {
                    if (data.camera_running == 1) {
                        camera.status = STATUS_AGENT_ON_CAMERA_ON;
                    }
                    else {
                        camera.status = STATUS_AGENT_ON_CAMERA_OFF;
                    }
                    updateControlPoint(camera.controlpoint);
                } 
                break;
                
            case "agent-disconnect":
                var camera = cameras.get(data.who);
                if (camera != undefined) {
                    camera.status = STATUS_AGENT_OFF;
                    updateControlPoint(camera.controlpoint);
                    alert("Conex\xE3o interrompida entre o monitor e o agente da c\xE2mera " + (camera.controlpoint.cameras.indexOf(camera) + 1)
                          + " do ponto de controle '" + camera.controlpoint.name + "'.");
                } 
                break;
                
            case "agent-processing-rate":
                if (data.target == id) {
                    var camera = cameras.get(data.who);
                    if (camera != undefined) {
                        alert("O agente da c\xE2mera " + (camera.controlpoint.cameras.indexOf(camera) + 1)
                              + " do ponto de controle '" + camera.controlpoint.name + "' reportou"
                              + " processamento a " + data.processing_rate + " quadros por segundo.");
                    }
                } 
                break;
                
            case "inventory":
                $.each(data.agents, function(_, pair) {
                    var camera = cameras.get(pair[0]); 
                    if (camera != undefined) {
                        if (pair[1]) {
                            camera.status = STATUS_AGENT_ON_CAMERA_ON;
                        }
                        else {
                            camera.status = STATUS_AGENT_ON_CAMERA_OFF;
                        }
                        updateControlPoint(camera.controlpoint);
                    }
                })
                break;
        }
    };

    socket.onclose = function(event) {
        alert("A conex\xE3o com o servidor foi interrompida.")
    };
}
