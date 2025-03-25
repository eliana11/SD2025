import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.io.*;
import java.net.*;
import java.util.*;

public class NodoD {
    private static List<Contact> registros = new ArrayList<>();
    private static Gson gson = new Gson(); // Instancia de Gson para la serialización/deserialización

    public static void main(String[] args) {
        int puerto = 12347; // Puerto fijo para el servidor D
        try {
            ServerSocket serverSocket = new ServerSocket(puerto);
            System.out.println("Servidor D escuchando en puerto " + puerto);

            while (true) {
                // Aceptar nueva conexión (nuevo nodo C)
                Socket socket = serverSocket.accept();
                System.out.println("Conexión aceptada desde: " + socket.getInetAddress());

                // Crear streams de entrada y salida
                BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                PrintWriter out = new PrintWriter(socket.getOutputStream(), true);

                // Recibir los datos de contacto (IP y puerto) del nodo C
                String registroJson = in.readLine();
                Contact registro = gson.fromJson(registroJson, Contact.class);

                // Registrar el nodo C
                registros.add(registro);

                // Responder con la lista de nodos registrados
                JsonObject respuesta = new JsonObject();
                respuesta.add("nodos", registrosToJson());
                out.println(respuesta.toString());

                // Cerrar conexiones
                in.close();
                out.close();
                socket.close();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // Convierte la lista de nodos registrados a JsonArray utilizando Gson
    private static JsonArray registrosToJson() {
        JsonArray jsonArray = new JsonArray();
        for (Contact contacto : registros) {
            JsonObject jsonContacto = new JsonObject();
            jsonContacto.addProperty("ip", contacto.getIp());
            jsonContacto.addProperty("puerto", contacto.getPuerto());
            jsonArray.add(jsonContacto);
        }
        return jsonArray;
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
