from worker.Usuario import UsuarioBlockchain
import requests
usuario1 = UsuarioBlockchain(nombre = "001", coordinador_url="http://localhost:5000")
usuario2 = UsuarioBlockchain(nombre = "002", coordinador_url="http://localhost:5000")

usuario1.registar()
usuario2.registar()

usuario1.enviar_transaccion(monto= 100, destino= usuario2.direccion)