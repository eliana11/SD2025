
import java.io.*;
import java.net.*;

public class Nodo{

    public static void main(String[] args) {
        if (args.length != 4) {
            System.out.println("Uso: java ProgramaC <IP_Servidor> <Puerto_Servidor> <IP_Cliente> <Puerto_Cliente>");
            return;
        }

        String ipServidor = args[0];
        int puertoServidor = Integer.parseInt(args[1]);
        String ipCliente = args[2];
        int puertoCliente = Integer.parseInt(args[3]);

        // Hilo para escuchar en el puerto del servidor
        Thread hiloServidor = new Thread(() -> iniciarServidor(puertoServidor));

        // Hilo para enviar un saludo al otro nodo
        Thread hiloCliente = new Thread(() -> iniciarCliente(ipCliente, puertoCliente));

        // Iniciar ambos hilos
        hiloServidor.start();
        hiloCliente.start();
    }

    // Método para iniciar el servidor (escuchar los saludos)
    public static void iniciarServidor(int puerto) {
        try (ServerSocket serverSocket = new ServerSocket(puerto)) {
            System.out.println("Servidor escuchando en el puerto " + puerto + "...");

            while (true) {
                Socket socket = serverSocket.accept();
                System.out.println("Conexión establecida con " + socket.getInetAddress());

                // Leer el saludo del cliente
                BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                String saludo = entrada.readLine();
                System.out.println("Recibido del cliente: " + saludo);

                // Responder al cliente
                PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
                salida.println("¡Hola desde el servidor!");

                socket.close();
            }
        } catch (IOException e) {
            System.out.println("Error en el servidor: " + e.getMessage());
        }
    }

    // Método para iniciar el cliente (enviar un saludo al servidor)
    public static void iniciarCliente(String ip, int puerto) {
        try {
            // Espera un poco para asegurarse de que el servidor esté listo
            Thread.sleep(1000);

            // Conectar al servidor
            Socket socket = new Socket(ip, puerto);
            System.out.println("Conectado al servidor en " + ip + ":" + puerto);

            // Enviar un saludo
            PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
            salida.println("¡Hola, servidor!");

            // Leer la respuesta del servidor
            BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            String respuesta = entrada.readLine();
            System.out.println("Respuesta del servidor: " + respuesta);

            socket.close();
        } catch (IOException | InterruptedException e) {
            System.out.println("Error en el cliente: " + e.getMessage());
        }
    }
}
