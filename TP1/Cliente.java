import java.io.*;
import java.net.*;

public class Cliente {
    public static void main(String[] args) {
        String direccionServidor = "127.0.0.1"; // IP del servidor (cambiar si es remoto)
        int puerto = 12345;

        try (Socket socket = new Socket(direccionServidor, puerto)) {
            // Flujo de entrada y salida
            PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            // Enviar mensaje al servidor
            salida.println("¡Hola, servidor!");

            // Recibir respuesta del servidor
            String respuesta = entrada.readLine();
            System.out.println("Servidor responde: " + respuesta);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}