from flask import Flask, render_template, request, abort, json
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import os
import atexit
import subprocess

USER_KEYS = ['uid', 'nombre', 'nacimiento', 'correo', 'nacionalidad',
             'contraseña']

MESSAGE_KEY = ["message", "sender", "receptant", "lat", "long", "date", "id"]

# Levantamos el servidor de mongo. Esto no es necesario, puede abrir
# una terminal y correr mongod. El DEVNULL hace que no vemos el output
#mongod = subprocess.Popen('mongod', stdout=subprocess.DEVNULL)
# Nos aseguramos que cuando el programa termine, mongod no quede corriendo
#atexit.register(mongod.kill)

# El cliente se levanta en localhost:5432
client = MongoClient('localhost')
# Utilizamos la base de datos 'entidades'
db = client["entrega4"]
# Seleccionamos la colección de usuarios
usuarios = db.usuarios
message = db.mensajes

message.drop_indexes()
message.create_index([("message", "text")])
# Iniciamos la aplicación de flask
app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Entrega 4</h1>"


@app.route("/users")
def get_users():
    resultados = [u for u in usuarios.find({}, {"_id": 0})]
    # Omitir el _id porque no es json serializable

    return json.jsonify(resultados)

@app.route("/info_message/<int:id>")
def get_info_message(id):
    msj = list(message.find({"id": str(id)}, {"_id": 0}))

    return json.jsonify(msj)


@app.route("/user/<int:uid>")
def get_user(uid):
    users = list(usuarios.find({"uid": uid}, {"_id": 0}))
    msj = list(message.find({"sender": str(uid)}, {"_id": 0}))

    return json.jsonify(users, msj)


# entrega los mensajes hechos por el uid1 y hacia el uid 2
@app.route("/message/<int:uid1>/<int:uid2>")
def get_message(uid1, uid2):
    msj = list(message.find({"$and":[{"sender": str(uid1)},{"receptant": str(uid2)}]},
                            {"_id": 0}))
    msj2 = list(message.find({"$and": [{"sender": str(uid2)}, {"receptant": str(uid1)}]},
                            {"_id": 0}))

    return json.jsonify(msj, msj2)


@app.route("/buscar_siempre")
def buscar_siempre():
    #get
    try:
        uid = request.json.get("uid")
    except:
        uid = None

    palabras = request.json.get("palabras")
    string = ""
    for p in palabras:
        string += f"\"{p}\""
    if uid:
        msj = list(message.find({"$and": [{"sender": str(uid)}, {"$text": {"$search": string}}]},
                                {"_id": 0}))
    else:
        msj = list(message.find({"$text": {"$search": string}},
                            {"_id": 0}))

    return json.jsonify(msj)

@app.route("/buscar_deseables")
def buscar_deseables():
    #get
    try:
        uid = request.json.get("uid")
    except:
        uid = None

    palabras = request.json.get("palabras")
    string = ""
    for p in palabras:
        string += f"{p} "
    if uid:
        msj = list(message.find({"$and": [{"sender": str(uid)}, {"$text": {"$search": string}}]},
                                {"_id": 0}))
    else:
        msj = list(message.find({"$text": {"$search": string}},
                            {"_id": 0}))

    return json.jsonify(msj)


@app.route("/buscar_nunca")
def buscar_nunca():
    #get
    try:
        uid = request.json.get("uid")
    except:
        uid = None

    palabras = request.json.get("palabras")
    string = ""
    for p in palabras:
        string += f"{p} "
    if uid:
        msj = list(message.find({"$and": [{"sender": str(uid)}, {"$text": {"$search": string}}]},
                                {"_id": 0}))
    else:
        msj = list(message.find({"$text": {"$search": string}},
                            {"_id": 0}))

    todos = list(message.find({}, {"_id": 0}))
    #resultado = set(todos) - set(msj)
    #resultado = list(resultado)
    copia = todos
    for i in todos:
        if i in msj:
            copia.remove(i)
    return json.jsonify(copia)

@app.route("/message/<int:uid1>/<int:uid2>", methods=['POST'])
def create_msj(uid1, uid2):

    # Si los parámetros son enviados con una request de tipo application/json:
    data = {key: request.json.get(key) for key in MESSAGE_KEY}

    data["sender"] = str(uid1)
    data["receptant"] = str(uid2)

    # Se genera el uid
    count = message.count_documents({})
    data["id"] = count + 1

    # Insertar retorna un objeto
    result = message.insert_one(data)

    # Creo el mensaje resultado
    if (result):
        msje = "1 mensaje creado"
        success = True
    else:
        msje = "No se pudo crear el mensaje"
        success = False

    # Retorno el texto plano de un json
    return json.jsonify({'success': success, 'message': msje})

@app.route("/users", methods=['POST'])
def create_user():
    '''
    Crea un nuevo usuario en la base de datos
    Se  necesitan todos los atributos de model, a excepcion de _id
    '''

    # Si los parámetros son enviados con una request de tipo application/json:
    data = {key: request.json.get(key) for key in USER_KEYS}

    # Se genera el uid
    count = usuarios.count_documents({})
    data["uid"] = count + 1

    # Insertar retorna un objeto
    result = usuarios.insert_one(data)

    # Creo el mensaje resultado
    if (result):
        msje = "1 usuario creado"
        success = True
    else:
        msje = "No se pudo crear el usuario"
        success = False

    # Retorno el texto plano de un json
    return json.jsonify({'success': success, 'message': msje})


@app.route('/mensaje/<int:id>', methods=['DELETE'])
def delete_message(id):
    '''
    Elimina un usuario de la db.
    Se requiere llave uid
    '''

    # esto borra el primer resultado. si hay mas, no los borra
    message.delete_one({"id": str(id)})

    msje = f'Mensaje con id={id} ha sido eliminado.'

    # Retorno el texto plano de un json
    return json.jsonify({'result': 'success', 'message': msje})


@app.route('/users/many', methods=['DELETE'])
def delete_many_user():
    '''
    Elimina un varios usuarios de la db.
    - Se requiere llave idBulk en el body de la request application/json
    '''

    if not request.json:
        # Solicitud faltan parametros. Codigo 400: Bad request
        abort(400)  # Arrojar error

    all_uids = request.json['uidBulk']

    if not all_uids:
        # Solicitud faltan parametros. Codigo 400: Bad request
        abort(400)  # Arrojar error

    # Esto borra todos los usuarios con el id dentro de la lista
    result = usuarios.delete_many({"uid": {"$in": all_uids}})

    # Creo el mensaje resultado
    msje = f'{result.deleted_count} usuarios eliminados.'

    # Retorno el texto plano de un json
    return json.jsonify({'result': 'success', 'message': msje})


@app.route("/test")
def test():
    # Obtener un parámero de la URL
    param = request.args.get('name', False)
    print("URL param:", param)

    # Obtener un header
    param2 = request.headers.get('name', False)
    print("Header:", param2)

    # Obtener el body
    body = request.data
    print("Body:", body)

    return "OK"


if os.name == 'nt':
    app.run()
