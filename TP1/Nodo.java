import java.io.*;
import java.net.*;

public class Nodo {
    private String ipDestino;
    private int puertoDestino;
    private int puertoLocal;

    public Nodo(String ipDestino, int puertoDestino, int puertoLocal) {
        this.ipDestino = ipDestino;
        this.puertoDestino = puertoDestino;
        this.puertoLocal = puertoLocal;
    }

    public void iniciar() {
        // Iniciar servidor en un hilo separado
        new Thread(this::iniciarServidor).start();

        // Esperar un momento antes de iniciar el cliente
        try {
            Thread.sleep(2000); // Para asegurarse de que el otro nodo esté listo
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        // Iniciar cliente para conectarse al otro nodo
        iniciarCliente();
    }

    private void iniciarServidor() {
        try (ServerSocket servidor = new ServerSocket(puertoLocal)) {
            System.out.println("Nodo escuchando en el puerto " + puertoLocal + "...");

            while (true) {
                Socket socket = servidor.accept();
                System.out.println("Conexión establecida con " + socket.getInetAddress());

                try (BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                     PrintWriter salida = new PrintWriter(socket.getOutputStream(), true)) {

                    // Leer mensaje del otro nodo
                    String mensaje = entrada.readLine();
                    System.out.println("Nodo dice: " + mensaje);

                    // Responder
                    salida.println("¡Hola, nodo! Conexión exitosa.");
                }
                socket.close();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void iniciarCliente() {
        try (Socket socket = new Socket(ipDestino, puertoDestino)) {
            System.out.println("Conectado a nodo " + ipDestino + ":" + puertoDestino);

            try (PrintWriter salida = new PrintWriter(socket.getOutputStream(), true);
                 BufferedReader entrada = new BufferedReader(new InputStreamReader(socket.getInputStream()))) {

                // Enviar mensaje
                salida.println("¡Hola, nodo!");

                // Recibir respuesta
                String respuesta = entrada.readLine();
                System.out.println("Nodo responde: " + respuesta);
            }
        } catch (IOException e) {
            System.out.println("No se pudo conectar con el nodo destino.");
        }
    }

    public static void main(String[] args) {
        if (args.length < 3) {
            System.out.println("Uso: java Nodo <IP_DESTINO> <PUERTO_DESTINO> <PUERTO_LOCAL>");
            return;
        }

        String ipDestino = args[0];
        int puertoDestino = Integer.parseInt(args[1]);
        int puertoLocal = Integer.parseInt(args[2]);

        Nodo nodo = new Nodo(ipDestino, puertoDestino, puertoLocal);
        nodo.iniciar();
    }
}
