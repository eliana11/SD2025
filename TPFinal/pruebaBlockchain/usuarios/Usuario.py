from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
import hashlib
import json
import base64

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
