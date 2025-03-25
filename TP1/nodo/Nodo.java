import java.io.*;
import java.net.*;
import java.util.concurrent.*;
import com.google.gson.Gson;

class Mensaje {
    String tipo;
    String contenido;

    Mensaje(String tipo, String contenido) {
        this.tipo = tipo;
        this.contenido = contenido;
    }
}

public class Nodo {
    private static final Gson gson = new Gson();

    private static void iniciarServidor(int puerto) {
        ExecutorService executor = Executors.newFixedThreadPool(5);
        try (ServerSocket serverSocket = new ServerSocket(puerto)) {
            System.out.println("[SERVIDOR] Escuchando en el puerto " + puerto);
            
            while (true) {
                Socket socket = serverSocket.accept();
                executor.execute(() -> manejarConexion(socket));
            }
        } catch (IOException e) {
            System.err.println("[SERVIDOR] Error: " + e.getMessage());
        }
    }

    private static void manejarConexion(Socket socket) {
        try (BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
             PrintWriter out = new PrintWriter(socket.getOutputStream(), true)) {
            
            System.out.println("[SERVIDOR] Conexión establecida con " + socket.getRemoteSocketAddress());
            String mensajeJson;
            while ((mensajeJson = in.readLine()) != null) {
                Mensaje mensaje = gson.fromJson(mensajeJson, Mensaje.class);
                System.out.println("[SERVIDOR] Mensaje recibido: " + mensaje.contenido);
                
                Mensaje respuesta = new Mensaje("respuesta", "Hola, cliente!");
                out.println(gson.toJson(respuesta));
            }
        } catch (IOException e) {
            System.err.println("[SERVIDOR] Cliente desconectado abruptamente");
        }
    }

    private static void iniciarCliente(String ip, int puerto) {
        while (true) {
            try (Socket socket = new Socket(ip, puerto);
                 PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
                 BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()))) {
                
                System.out.println("[CLIENTE] Conectado a " + ip + ":" + puerto);
                
                while (true) {
                    Mensaje mensaje = new Mensaje("saludo", "Hola, servidor!");
                    out.println(gson.toJson(mensaje));
                    
                    String respuestaJson = in.readLine();
                    Mensaje respuesta = gson.fromJson(respuestaJson, Mensaje.class);

                    String mensajeJson = gson.toJson(mensaje);
                    System.out.println("[CLIENTE] Enviando mensaje: " + mensajeJson);
                    out.println(mensajeJson);
                    

                    System.out.println("[CLIENTE] Respuesta recibida: " + respuesta.contenido);
                    
                    Thread.sleep(5000);
                }
            } catch (IOException | InterruptedException e) {
                System.out.println("[CLIENTE] No se pudo conectar a " + ip + ":" + puerto + ". Reintentando en 5 segundos...");
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException ignored) {}
            }
        }
    }

    public static void main(String[] args) {
        if (args.length != 3) {
            System.out.println("Uso: java Nodo <puerto_escucha> <ip_destino> <puerto_destino>");
            return;
        }
        
        int puertoEscucha = Integer.parseInt(args[0]);
        String ipDestino = args[1];
        int puertoDestino = Integer.parseInt(args[2]);
        
        new Thread(() -> iniciarServidor(puertoEscucha)).start();
        iniciarCliente(ipDestino, puertoDestino);
    }
}