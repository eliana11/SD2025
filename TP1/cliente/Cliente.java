import java.io.*;
import java.net.*;


public class Cliente {
    public static void main(String[] args) {
        String direccionServidor = "servidor"; // IP del servidor
        int puerto = 8080;
        int intentosMaximos = 5; // Máximo número de intentos de reconexión
        int tiempoEspera = 3000; // Tiempo de espera entre intentos (ms)

        while (true) {
            try (Socket socket = new Socket(direccionServidor, puerto);
                 PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
                 BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()))) {

                System.out.println("Conectado al servidor en " + direccionServidor + ":" + puerto);


                // Enviar mensaje al servidor
                salida.println("¡Hola, servidor!");

                // Recibir respuesta del servidor
                String respuesta = entrada.readLine();
                if (respuesta != null) {
                    System.out.println("Servidor responde: " + respuesta);
                } else {
                    throw new IOException("Conexión cerrada por el servidor.");
                }

                break; // Si el mensaje fue enviado con éxito, salir del bucle

            } catch (IOException e) {
                System.err.println("Error: " + e.getMessage());
                System.err.println("Intentando reconectar...");

                boolean reconectado = false;
                for (int i = 1; i <= intentosMaximos; i++) {
                    try {
                        Thread.sleep(tiempoEspera); // Esperar antes de intentar de nuevo
                        System.out.println("Intento #" + i + " de reconexión...");
                        new Socket(direccionServidor, puerto).close(); // Probar la conexión
                        reconectado = true;
                        break;
                    } catch (IOException | InterruptedException ex) {
                        System.err.println("Reconexión fallida.");
                    }
                }

                if (!reconectado) {
                    System.err.println("No se pudo reconectar después de " + intentosMaximos + " intentos. Cerrando cliente.");
                    break;
                }
            }
        }
    }
}