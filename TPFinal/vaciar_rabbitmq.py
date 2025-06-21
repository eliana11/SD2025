import pika

# Conexión
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Vaciar la cola (por ejemplo: "mining_tasks")
channel.queue_purge(queue='mining_tasks')

print("✅ Cola vaciada.")
connection.close()
