from worker.Usuario import UsuarioBlockchain
import requests
usuario1 = UsuarioBlockchain(nombre = "001", coordinador_url="http://35.192.66.105:80")
usuario2 = UsuarioBlockchain(nombre = "002", coordinador_url="http://35.192.66.105:80")

usuario1.registar()
usuario2.registar()

usuario1.enviar_transaccion(monto= 100, destino= usuario2.direccion)