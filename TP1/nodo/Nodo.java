import java.io.*;
import java.net.*;
import com.google.gson.Gson; // Importar la librería Gson

public class Nodo {
    
    private static final Gson gson = new Gson(); // Instancia de Gson

    public static void main(String[] args) {
        if (args.length != 4) {
            System.out.println("Uso: java Nodo <IP_Servidor> <Puerto_Servidor> <IP_Cliente> <Puerto_Cliente>");
            return;
        }

        int puertoServidor = Integer.parseInt(args[1]);
        String ipCliente = args[2];
        int puertoCliente = Integer.parseInt(args[3]);

        // Iniciar servidor en un hilo
        Thread hiloServidor = new Thread(() -> iniciarServidor(puertoServidor));
        hiloServidor.start();

        // Iniciar cliente en otro hilo
        Thread hiloCliente = new Thread(() -> iniciarCliente(ipCliente, puertoCliente));
        hiloCliente.start();
    }

    // Clase interna para representar el mensaje JSON
    static class Mensaje {
        String origen;
        String contenido;

        Mensaje(String origen, String contenido) {
            this.origen = origen;
            this.contenido = contenido;
        }
    }

    // Método para iniciar el servidor (escuchar mensajes)
    public static void iniciarServidor(int puerto) {
        try (ServerSocket serverSocket = new ServerSocket(puerto)) {
            System.out.println("Servidor escuchando en el puerto " + puerto + "...");

            while (true) {
                Socket socket = serverSocket.accept();
                System.out.println("Conexión establecida con " + socket.getInetAddress());

                // Leer el mensaje JSON del cliente
                BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                String mensajeJson = entrada.readLine();
                
                // Deserializar el mensaje JSON
                Mensaje mensaje = gson.fromJson(mensajeJson, Mensaje.class);
                System.out.println("Recibido de " + mensaje.origen + ": " + mensaje.contenido);

                // Enviar respuesta en JSON
                PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
                Mensaje respuesta = new Mensaje("Servidor", "¡Hola desde el servidor!");
                salida.println(gson.toJson(respuesta));

                socket.close();
            }
        } catch (IOException e) {
            System.out.println("Error en el servidor: " + e.getMessage());
        }
    }

    // Método para iniciar el cliente (enviar un mensaje)
    public static void iniciarCliente(String ip, int puerto) {
        try {
            Thread.sleep(1000); // Esperar para que el servidor esté listo

            Socket socket = new Socket(ip, puerto);
            System.out.println("Conectado al servidor en " + ip + ":" + puerto);

            // Crear mensaje en formato JSON
            PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
            Mensaje mensaje = new Mensaje("Cliente", "¡Hola, servidor!");
            salida.println(gson.toJson(mensaje));

            // Leer la respuesta JSON del servidor
            BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            String respuestaJson = entrada.readLine();
            
            // Deserializar la respuesta
            Mensaje respuesta = gson.fromJson(respuestaJson, Mensaje.class);
            System.out.println("Respuesta del servidor: " + respuesta.contenido);

            socket.close();
        } catch (IOException | InterruptedException e) {
            System.out.println("Error en el cliente: " + e.getMessage());
        }
    }
}
