from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
import hashlib
import json
import base64
import requests
import time

class UsuarioBlockchain:
    def __init__(self, nombre=None):
        if nombre:
            self._generar_wallet_personalizada(nombre)
        else:
            self.clave_privada = ec.generate_private_key(ec.SECP256K1())
            self.clave_publica = self.clave_privada.public_key()
            self.direccion = self._generar_direccion()

    def _generar_direccion(self):
        pub_bytes = self.clave_publica.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(pub_bytes).hexdigest()

    def _generar_wallet_personalizada(self, nombre):
        wallet = None
        intentos = 0
        while not wallet:
            intentos += 1
            clave_privada = ec.generate_private_key(ec.SECP256K1())
            clave_publica = clave_privada.public_key()
            pub_bytes = clave_publica.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            direccion = hashlib.sha256(pub_bytes).hexdigest()
            if direccion.endswith(nombre):
                wallet = (clave_privada, clave_publica, direccion)
        print(f"[✓] Wallet personalizada encontrada en {intentos} intentos.")
        self.clave_privada, self.clave_publica, self.direccion = wallet

    def firmar_transaccion(self, transaccion: dict) -> str:
        mensaje = json.dumps(transaccion, sort_keys=True).encode()
        firma = self.clave_privada.sign(mensaje, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(firma).decode()

    def exportar_clave_publica(self) -> str:
        return self.clave_publica.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def exportar_clave_privada(self) -> str:
        return self.clave_privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
    
    def registar(self, url="http://localhost:5000/registro"):
        data = {
            "clave_publica": self.exportar_clave_publica()
        }
        try:
            response = requests.post(url, json=data)
            if response.status_code == 201:
                print("[✅] Registro exitoso:", response.json())
            else:
                print("[❌] Error al registrar:", response.status_code, response.text)
        except Exception as e:
            print("[💥] Excepción durante el registro:", e)
    
    def enviar_transaccion(self, destino, monto, url_coordinador="http://localhost:5000/transaccion"):
        transaccion = {
            "de": self.direccion,
            "para": destino,
            "monto": monto,
        }

        firma = self.firmar_transaccion(transaccion)
        clave_publica = self.exportar_clave_publica()

        datos = {
            "transaccion": transaccion,
            "clave_publica": clave_publica,
            "firma": firma
        }

        response = requests.post(url_coordinador, json=datos)

        if response.status_code == 201:
            print("[✅] Transacción enviada con éxito:", response.json())
        else:
            print("[❌] Error al enviar transacción:", response.status_code, response.text)