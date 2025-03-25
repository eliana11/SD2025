import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;
import java.io.*;
import java.net.*;
import java.util.*;

public class NodoC {
    private static Gson gson = new Gson(); // Instancia de Gson para serialización y deserialización
    private final int puertoLocal; // Puerto en el que escucha el nodo C
    private final String ipNodoD; // IP del nodo D
    private final int puertoNodoD; // Puerto del nodo D
    private List<Contact> nodosC = new ArrayList<>(); // Lista de nodos C registrados

    public NodoC(int puertoLocal, String ipNodoD, int puertoNodoD) {
        this.puertoLocal = puertoLocal;
        this.ipNodoD = ipNodoD;
        this.puertoNodoD = puertoNodoD;
    }

    public static void main(String[] args) {
        if (args.length != 2) {
            System.out.println("Uso: java NodoC <ip_nodoD> <puerto_nodoD>");
            return;
        }

        NodoC nodoC = new NodoC(10000 + (int)(Math.random() * 10000), args[0], Integer.parseInt(args[1]));
        new Thread(() -> nodoC.iniciarEscucha()).start();
        nodoC.iniciarEnD();
    }

    private void iniciarEscucha() {
        try {
            ServerSocket serverSocket = new ServerSocket(puertoLocal);
            System.out.println("Nodo C escuchando en el puerto " + puertoLocal);
            while (true) {
                Socket socketCliente = serverSocket.accept();
                System.out.println("Conexión recibida de: " + socketCliente.getInetAddress());
                // Lógica para manejar la conexión
                BufferedReader in = new BufferedReader(new InputStreamReader(socketCliente.getInputStream()));
                String mensajeJson = in.readLine(); 
                JsonObject mensaje = gson.fromJson(mensajeJson, JsonObject.class);
                System.out.println("Mensaje recibido: " + mensaje.get("mensaje").getAsString());
                // Responder al mensaje 
                PrintWriter out = new PrintWriter(socketCliente.getOutputStream(), true);   
                JsonObject respuesta = new JsonObject();
                respuesta.addProperty("mensaje", "Hola, recibido, soy un nodo C!");
                out.println(gson.toJson(respuesta));
                // Cerrar la conexión
                in.close();
                out.close();
                socketCliente.close();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void iniciarEnD() {
        try {
            // Crear registro con datos del nodo C
            JsonObject registro = new JsonObject();
            registro.addProperty("ip", InetAddress.getLocalHost().getHostAddress());
            registro.addProperty("puerto", puertoLocal);

            // Conectar con Nodo D para registrarse
            Socket socketD = new Socket(ipNodoD, puertoNodoD);
            PrintWriter out = new PrintWriter(socketD.getOutputStream(), true);
            
            // Enviar la información del nodo C (IP y puerto)
            out.println(gson.toJson(registro));
            
            // Escuchar respuesta
            BufferedReader in = new BufferedReader(new InputStreamReader(socketD.getInputStream()));
            String mensaje = in.readLine();
            System.out.println("Respuesta de D: " + mensaje);

            JsonObject respuesta = gson.fromJson(mensaje, JsonObject.class);

            JsonArray nodosJson = respuesta.getAsJsonArray("nodos");
        
            // Parsear los nodos registrados y conectarse a cada uno para saludar
            this.nodosC = parseNodos(nodosJson);

            // Cerrar conexiones con Nodo D
            in.close();
            out.close();
            socketD.close();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // Conectarse a un nodo y saludar
    private static void conectarYSaludar(Contact nodo) throws IOException {
        Socket socket = new Socket(nodo.getIp(), nodo.getPuerto());
        PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
        BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

        // Enviar saludo
        JsonObject saludo = new JsonObject();
        saludo.addProperty("mensaje", "Hola, soy un nodo C!");
        out.println(gson.toJson(saludo));
        System.out.println("Saludo enviado a " + nodo.getIp() + ":" + nodo.getPuerto());

        // Leer la respuesta
        String respuestaJson = in.readLine();
        JsonObject respuesta = gson.fromJson(respuestaJson, JsonObject.class);
        System.out.println("Respuesta de " + nodo.getIp() + ":" + nodo.getPuerto() + " -> " + respuesta.get("mensaje").getAsString());

        // Cerrar conexión
        in.close();
        out.close();
        socket.close();
    }

    // Parsear la lista de nodos C desde el JSON
    private static List<Contact> parseNodos(JsonArray nodosJson) {
        List<Contact> nodosC = new ArrayList<>();
        for (int i = 0; i < nodosJson.size(); i++) {
            JsonObject nodoJson = nodosJson.get(i).getAsJsonObject();
            String ip = nodoJson.get("ip").getAsString();
            int puerto = nodoJson.get("puerto").getAsInt();
            try{
                if(ip != InetAddress.getLocalHost().getHostAddress()){
                    nodosC.add(new Contact(ip, puerto));
                }
            }
            catch (UnknownHostException e){
                e.printStackTrace();
            }
        }
        return nodosC;
    }

    // Clase para almacenar los contactos
    static class Contact {
        private String ip;
        private int puerto;

        public Contact(String ip, int puerto) {
            this.ip = ip;
            this.puerto = puerto;
        }

        public String getIp() {
            return ip;
        }

        public int getPuerto() {
            return puerto;
        }
    }
}
