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

            // Nombre del contenedor según la tarea
            String contenedor = "bautista222221/" + nombreTarea + ":v1";
            String containerName = "instancia_" + nombreTarea;

            // Verificar si el contenedor ya está corriendo
            Process check = Runtime.getRuntime().exec("docker ps -q -f name=" + containerName);
            BufferedReader checkReader = new BufferedReader(new InputStreamReader(check.getInputStream()));
            if (checkReader.readLine() == null) {
                // Si no está corriendo, lo ejecuta
                System.out.println("🚀 Lanzando contenedor: " + contenedor);
                
                Runtime.getRuntime().exec(new String[] {
                    "docker", "run", "-d", "--rm",
                    "--name", containerName,
                    "-p", puertoHost +":8080", // El contenedor expone en 8080
                    contenedor
                });
                // Espera unos segundos para que el contenedor esté listo
                Thread.sleep(3000);
            } else {
                System.out.println("✅ Contenedor ya está corriendo.");
            }

            // Enviar POST al contenedor
            URL url = new URL("http://localhost:"+puertoHost+"/" + nombreTarea);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            OutputStream os = conn.getOutputStream();
            os.write(inputJson.getBytes());
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