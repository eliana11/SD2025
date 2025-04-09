package src;
import com.sun.net.httpserver.*;

import java.io.*;
import java.net.*;
import java.util.*;
import org.json.JSONObject;
import org.json.JSONArray;

public class Servidor {
    public static void main(String[] args) throws IOException {

        HttpServer server = HttpServer.create(new InetSocketAddress(8000), 0);
        server.createContext("/getRemoteTask", new TaskHandler());
        server.createContext("/tareasDisponibles", new ListaTareasHandler()); // Nuevo endpoint
        server.setExecutor(null);
        server.start();
        System.out.println("Servidor corriendo en puerto 8000...");
    }
}

// Handler original para ejecutar tareas remotas
class TaskHandler implements HttpHandler {
    public void handle(HttpExchange exchange) throws IOException {
        System.out.println("📥 Nueva solicitud recibida: " + exchange.getRequestMethod() + " " + exchange.getRequestURI());
        if (!exchange.getRequestMethod().equalsIgnoreCase("POST")) {
            sendResponse(exchange, 405, "Método no permitido");
            return;
        }

        BufferedReader br = new BufferedReader(new InputStreamReader(exchange.getRequestBody(), "utf-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) {
            sb.append(line);
        }

        String inputJson = sb.toString();

        try {
            JSONObject input = new JSONObject(inputJson);
            String nombreTarea = input.getString("nombreTarea");

            int puertoHost;
            if (nombreTarea.equals("sumar")) {
                puertoHost = 8081;
            } else if (nombreTarea.equals("multiplicar")) {
                puertoHost = 8082;
            } else {
                puertoHost = 8083; // o lanzar error
            }

            String contenedor = "bautista222221/tarea-" + nombreTarea + ":v1";
            String containerName = "instancia_" + nombreTarea;

            // Verificar si el contenedor ya está corriendo
            Process check = Runtime.getRuntime().exec("docker ps -q -f name=" + containerName);
            BufferedReader checkReader = new BufferedReader(new InputStreamReader(check.getInputStream()));
            if (checkReader.readLine() == null) {
                System.out.println("🚀 Lanzando contenedor: " + contenedor);
                Runtime.getRuntime().exec(new String[] {
                    "docker", "run", "-d", "--rm",
                    "--name", containerName,
                    "-p", puertoHost + ":8080",
                    contenedor
                });
                Thread.sleep(3000);
            } else {
                System.out.println("✅ Contenedor ya está corriendo.");
            }

            // Preparar JSON filtrado para el contenedor
            JSONObject jsonToSend = new JSONObject();

            // Pasar "parametros"
            if (input.has("parametros")) {
                jsonToSend.put("parametros", input.getJSONArray("parametros"));
            } else {
                sendResponse(exchange, 400, "Faltan los parámetros requeridos.");
                return;
            }

            // Pasar "delayMs" si está presente
            if (input.has("delayMs")) {
                jsonToSend.put("delayMs", input.getInt("delayMs"));
            }

            // Enviar POST al contenedor
            URL url = new URL("http://localhost:" + puertoHost + "/" + nombreTarea);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            OutputStream os = conn.getOutputStream();
            os.write(jsonToSend.toString().getBytes("utf-8"));
            os.flush();
            os.close();

            int responseCode = conn.getResponseCode();
            BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            String inputLine;
            StringBuilder responseSb = new StringBuilder();
            while ((inputLine = in.readLine()) != null) {
                responseSb.append(inputLine);
            }
            in.close();

            sendResponse(exchange, responseCode, responseSb.toString());

        } catch (Exception e) {
            e.printStackTrace();
            sendResponse(exchange, 500, "Error al procesar la tarea: " + e.getMessage());
        }
    }

    private void sendResponse(HttpExchange exchange, int statusCode, String response) throws IOException {
        exchange.sendResponseHeaders(statusCode, response.getBytes().length);
        OutputStream os = exchange.getResponseBody();
        os.write(response.getBytes());
        os.close();
    }
}

// 🔄 Nuevo handler para informar tareas disponibles
class ListaTareasHandler implements HttpHandler {
    public void handle(HttpExchange exchange) throws IOException {
        if (!exchange.getRequestMethod().equalsIgnoreCase("GET")) {
            exchange.sendResponseHeaders(405, -1);
            return;
        }

        JSONArray tareasArray = new JSONArray();

        try {
            URL url = new URL("https://hub.docker.com/v2/repositories/bautista222221/?page_size=100");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");

            BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder response = new StringBuilder();
            String inputLine;
            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }
            in.close();

            JSONObject json = new JSONObject(response.toString());
            JSONArray results = json.getJSONArray("results");

            for (int i = 0; i < results.length(); i++) {
                String name = results.getJSONObject(i).getString("name");
            
                // Filtro: solo imágenes que empiecen con "tarea-"
                if (name.startsWith("tarea-")) {
                    String nombreTarea = name.replace("tarea-", ""); // le quitás el prefijo si querés
                    tareasArray.put(nombreTarea);
                }
            }
            

        } catch (Exception e) {
            e.printStackTrace();
            exchange.sendResponseHeaders(500, -1);
            return;
        }

        JSONObject respuesta = new JSONObject();
        respuesta.put("tareasDisponibles", tareasArray);

        byte[] bytes = respuesta.toString().getBytes("UTF-8");
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(200, bytes.length);
        OutputStream os = exchange.getResponseBody();
        os.write(bytes);
        os.close();
    }
}