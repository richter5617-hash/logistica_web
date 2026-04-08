# Instalar librerías necesarias:
# pip install flask geopy ortools

from flask import Flask, request, redirect
import urllib.parse
from geopy.geocoders import Nominatim
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

app = Flask(__name__)
geolocator = Nominatim(user_agent="logistica_web")

def geocodificar(direcciones):
    coords = []
    for d in direcciones:
        if d.strip() != "":
            loc = geolocator.geocode(d)
            if loc:
                coords.append((loc.latitude, loc.longitude))
    return coords

def crear_matriz_distancias(coords):
    # Calcula matriz de distancias en km
    size = len(coords)
    matriz = [[0]*size for _ in range(size)]
    from geopy.distance import geodesic
    for i in range(size):
        for j in range(size):
            if i != j:
                matriz[i][j] = int(geodesic(coords[i], coords[j]).km)
    return matriz

def optimizar_ruta(coords, num_vehiculos=1, deposito=0):
    # Crear matriz de distancias
    dist_matrix = crear_matriz_distancias(coords)

    # Crear gestor de índices
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehiculos, deposito)

    # Crear modelo de enrutamiento
    routing = pywrapcp.RoutingModel(manager)

    def distancia_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distancia_callback)

    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Parámetros de búsqueda
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Resolver
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        ruta = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            ruta.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return ruta
    else:
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        direcciones = request.form.getlist("direccion")
        coords = geocodificar(direcciones)
        ruta_indices = optimizar_ruta(coords)

        # Construir URL de Google Maps con orden optimizado
        base_url = "https://www.google.com/maps/dir/"
        ruta_optimizada = [direcciones[i] for i in ruta_indices]
        url = base_url + "/".join([urllib.parse.quote(d) for d in ruta_optimizada if d.strip() != ""])

        return redirect(url)

    # HTML incrustado con 15 campos
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Generador de Rutas Optimizado con OR-Tools</title>
    </head>
    <body>
        <h1>Generador de Rutas Optimizado en Google Maps</h1>
        <form method="POST">
            """ + "".join([f'<label>Cliente {i+1}:</label><br><input type="text" name="direccion"><br><br>' for i in range(15)]) + """
            <button type="submit">Generar Ruta Optimizada</button>
        </form>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)