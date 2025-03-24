import java.io.*;
import java.net.*;


public class Servidor {
   public static void main(String[] args) {
       int puerto = 8080; // Puerto de escucha


       try (ServerSocket servidor = new ServerSocket(puerto)) {
           System.out.println("Servidor esperando conexiones en el puerto " + puerto + "...");


           // Esperar conexión del cliente
           Socket socket = servidor.accept();
           System.out.println("Cliente conectado desde " + socket.getInetAddress());


           // Flujo de entrada y salida
           BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
           PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);


           // Leer mensaje del cliente
           String mensaje = entrada.readLine();
           System.out.println("Cliente dice: " + mensaje);


           // Responder al cliente
           salida.println("¡Hola, cliente! Conexión exitosa.");


           // Cerrar conexión
           socket.close();
       } catch (IOException e) {
           e.printStackTrace();
       }
   }
}
