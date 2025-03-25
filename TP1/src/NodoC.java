import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;
import java.io.*;
import java.net.*;
import java.util.*;

public class NodoC {
    private static Gson gson = new Gson(); // Instancia de Gson para serialización y deserialización

    public static void main(String[] args) {
        if (args.length != 2) {
            System.out.println("Uso: java NodoC <ip_nodoD> <puerto_nodoD>");
            return;
        }

        // Parámetros proporcionados
        String ipD = args[0];
        int puertoD = Integer.parseInt(args[1]);

        try {
            // Generar un puerto aleatorio para el nodo C
            int puertoC = 10000 + (int)(Math.random() * 10000);
            ServerSocket serverSocket = new ServerSocket(puertoC);
            System.out.println("Nodo C escuchando en puerto " + puertoC);

            // Conectar con Nodo D para registrarse
            Socket socketD = new Socket(ipD, puertoD);
            PrintWriter out = new PrintWriter(socketD.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socketD.getInputStream()));

            // Enviar la información del nodo C (IP y puerto)
            JsonObject registro = new JsonObject();
            registro.addProperty("ip", InetAddress.getLocalHost().getHostAddress());
            registro.addProperty("puerto", puertoC);
            out.println(gson.toJson(registro));

            // Recibir la lista de nodos C registrados desde D
            String respuestaJson = in.readLine();
            JsonObject respuesta = gson.fromJson(respuestaJson, JsonObject.class);
            JsonArray nodosJson = respuesta.getAsJsonArray("nodos");

            // Parsear los nodos registrados y conectarse a cada uno para saludar
            List<Contact> nodosC = parseNodos(nodosJson);
            for (Contact nodo : nodosC) {
                conectarYSaludar(nodo);
            }

            // Cerrar conexiones con Nodo D
            in.close();
            out.close();
            socketD.close();

            // Escuchar solicitudes de conexión de otros nodos
            while (true) {
                Socket socketCliente = serverSocket.accept();
                System.out.println("Conexión recibida de: " + socketCliente.getInetAddress());
                // Lógica para manejar la conexión
                socketCliente.close();
            }
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
