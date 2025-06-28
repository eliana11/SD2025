from worker.Usuario import UsuarioBlockchain
import requests
usuario1 = UsuarioBlockchain(nombre = "001", coordinador_url="http://35.192.66.105:80")
usuario2 = UsuarioBlockchain(nombre = "002", coordinador_url="http://35.192.66.105:80")

print("[INFO] Usuario 1 dirección:", usuario1.direccion)
print("[INFO] Usuario 2 dirección:", usuario2.direccion)

usuario1.registar()
usuario2.registar()

usuario1.enviar_transaccion(monto= 100, destino= usuario2.direccion)

# usuario3 = UsuarioBlockchain(nombre = "003", coordinador_url="http://35.192.66.105:80")
# usuario3.registar()
# usuario3.enviar_transaccion(monto= 50, destino= usuario1.direccion)
# usuario3.enviar_transaccion(monto= 50, destino= usuario2.direccion)

# usuario2.enviar_transaccion(monto= 20, destino= usuario1.direccion)
# usuario2.enviar_transaccion(monto= 30, destino= usuario3.direccion)

# Crear bucle para enviar n transacciones (testing)
