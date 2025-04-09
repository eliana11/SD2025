package src;
import com.sun.net.httpserver.*;

import java.io.*;
import java.net.*;
import org.json.JSONObject;


public class Servidor {
    public static void main(String[] args) throws IOException {
    
        HttpServer server = HttpServer.create(new InetSocketAddress(8000), 0);
        server.createContext("/getRemoteTask", new TaskHandler());
        server.setExecutor(null);
        server.start();
        System.out.println("Servidor corriendo en puerto 8000...");
    }
}

class TaskHandler implements HttpHandler {
    public void handle(HttpExchange exchange) throws IOException {
        System.out.println("📥 Nueva solicitud recibida: " + exchange.getRequestMethod() + " " + exchange.getRequestURI());
        if (!exchange.getRequestMethod().equalsIgnoreCase("POST")) {
            sendResponse(exchange, 405, "Método no permitido");
            return;
        }

        InputStreamReader isr = new InputStreamReader(exchange.getRequestBody(), "utf-8");
        BufferedReader br = new BufferedReader(isr);
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) {
            sb.append(line);
        }

        String inputJson = sb.toString();

        try {
            JSONObject input = new JSONObject(inputJson);
            String nombreTarea = input.getString("nombreTarea");

            // Validación opcional: tarea válida
            if (!nombreTarea.equals("sumar") && !nombreTarea.equals("promedio")) {
                sendResponse(exchange, 404, "Tarea no encontrada");
                return;
            }

            // Llamar al contenedor del servicio tarea
            URL url = new URL("http://localhost:8081/ejecutarTarea"); // nombre del contenedor
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            OutputStream os = conn.getOutputStream();
            os.write(inputJson.getBytes());
            os.flush();
            os.close();

            // Leer respuesta del servicio tarea
            int responseCode = conn.getResponseCode();
            BufferedReader in = new BufferedReader(
                new InputStreamReader(conn.getInputStream()));
            String inputLine;
            StringBuilder responseSb = new StringBuilder();

            while ((inputLine = in.readLine()) != null) {
                responseSb.append(inputLine);
            }
            in.close();

            // Enviar respuesta al cliente original
            sendResponse(exchange, responseCode, responseSb.toString());

        } catch (Exception e) {
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

