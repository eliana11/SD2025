import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;


public class Tarea {
    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(8081), 0);
        server.createContext("/ejecutarTarea", new TareaHandler());
        server.setExecutor(null);
        server.start();
        System.out.println("Servicio Tarea corriendo en puerto 8081...");
    }
}

class TareaHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
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

        try {
            JSONObject inputJson = new JSONObject(sb.toString());

            String tarea = inputJson.getString("nombreTarea");
            JSONArray parametros = inputJson.getJSONArray("parametros");
            int delay = inputJson.optInt("delayMs", 1000);

            double resultado = 0;

            switch (tarea) {
                case "sumar":
                    for (int i = 0; i < parametros.length(); i++) {
                        resultado += parametros.getDouble(i);
                    }
                    break;
                case "promedio":
                    for (int i = 0; i < parametros.length(); i++) {
                        resultado += parametros.getDouble(i);
                    }
                    resultado /= parametros.length();
                    break;
                default:
                    sendResponse(exchange, 404, "Tarea no encontrada");
                    return;
            }

            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            JSONObject output = new JSONObject();
            output.put("resultado", resultado);
            output.put("status", "ok");
            sendResponse(exchange, 200, output.toString());

        } catch (JSONException e) {
            sendResponse(exchange, 400, "Error en JSON de entrada");
        }
    }

    private void sendResponse(HttpExchange exchange, int statusCode, String response) throws IOException {
        exchange.sendResponseHeaders(statusCode, response.getBytes().length);
        OutputStream os = exchange.getResponseBody();
        os.write(response.getBytes());
        os.close();
    }
}
