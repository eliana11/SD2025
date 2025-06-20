from usuarios.Usuario import UsuarioBlockchain

usuario1 = UsuarioBlockchain(nombre = "001")
usuario2 = UsuarioBlockchain(nombre = "002")

usuario1.registar()
usuario2.registar()

usuario1.enviar_transaccion(monto= 100, destino= usuario2.direccion)