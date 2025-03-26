import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.*;
import java.net.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class NodoD {
    private final int puerto = 12347;
    private static final String ARCHIVO_INSCRIPCIONES = "inscripciones.json";
    private static final ZoneId ZONA_ARGENTINA = ZoneId.of("America/Argentina/Buenos_Aires");
    private static final Gson gson = new Gson();

    public NodoD() {
        actualizacionPeriodica();
    }

    private synchronized void registrar(String ip, String puerto, String horaRegistro) {
        try {
            List<JsonObject> inscripciones = cargarInscripciones();
            String ventanaTiempo = calcularVentanaSiguiente(horaRegistro);

            JsonObject nuevaInscripcion = new JsonObject();
            nuevaInscripcion.addProperty("ip", ip);
            nuevaInscripcion.addProperty("puerto", puerto);
            nuevaInscripcion.addProperty("ventana", ventanaTiempo);

            inscripciones.add(nuevaInscripcion);
            guardarInscripciones(inscripciones);
        } catch (Exception e) {
            System.err.println("Error registrando nodo: " + e.getMessage());
        }
    }

    private synchronized List<JsonObject> cargarInscripciones() {
        File archivo = new File(ARCHIVO_INSCRIPCIONES);
        if (!archivo.exists()) return new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(archivo))) {
            String contenido = reader.readLine();
            if (contenido == null || contenido.isEmpty()) return new ArrayList<>();
            JsonArray jsonArray = gson.fromJson(contenido, JsonArray.class);
            List<JsonObject> lista = new ArrayList<>();
            jsonArray.forEach(element -> lista.add(element.getAsJsonObject()));
            return lista;
        } catch (IOException e) {
            System.err.println("Error leyendo inscripciones: " + e.getMessage());
            return new ArrayList<>();
        }
    }

    private synchronized void guardarInscripciones(List<JsonObject> inscripciones) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(ARCHIVO_INSCRIPCIONES))) {
            writer.println(gson.toJson(inscripciones));
        } catch (IOException e) {
            System.err.println("Error guardando inscripciones: " + e.getMessage());
        }
    }

    private synchronized String calcularVentanaSiguiente(String hora) {
        LocalTime tiempo = LocalTime.parse(hora, DateTimeFormatter.ofPattern("HH:mm:ss")).withSecond(0);
        LocalTime siguienteVentana = tiempo.plusMinutes(1);
        return siguienteVentana.format(DateTimeFormatter.ofPattern("HH:mm"));
    }

    private synchronized String obtenerVentanaActual() {
        return LocalTime.now(ZONA_ARGENTINA).withSecond(0).format(DateTimeFormatter.ofPattern("HH:mm"));
    }

    private synchronized String obtenerInscripcionesActivas() {
        List<JsonObject> inscripciones = cargarInscripciones();
        String ventanaActual = obtenerVentanaActual();

        JsonArray activas = new JsonArray();
        for (JsonObject inscripcion : inscripciones) {
            if (inscripcion.get("ventana").getAsString().equals(ventanaActual)) {
                activas.add(inscripcion);
            }
        }
        return gson.toJson(activas);
    }

    private void actualizacionPeriodica() {
        Timer timer = new Timer(true);
        timer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                actualizarVentana();
            }
        }, 0, 60 * 1000);
    }

    private synchronized void notificarCambioVentana() {
        List<JsonObject> inscripciones = cargarInscripciones();
        String ventanaActual = obtenerVentanaActual();
        
        // Enviar notificación a cada NodoC
        for (JsonObject inscripcion : inscripciones) {
            String ipNodoC = inscripcion.get("ip").getAsString();
            int puertoNodoC = inscripcion.get("puerto").getAsInt();
            
            try {
                Socket socket = new Socket(ipNodoC, puertoNodoC);
                PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
                
                // Notificación de ventana actualizada
                JsonObject notificacion = new JsonObject();
                notificacion.addProperty("mensaje", "Cambio de ventana: " + ventanaActual);
                out.println(gson.toJson(notificacion));
                
                System.out.println("Notificación enviada a NodoC: " + ipNodoC);
                
                out.close();
                socket.close();
            } catch (IOException e) {
                System.err.println("Error al notificar a NodoC: " + e.getMessage());
            }
        }
    }
    
    // Llamar a este método después de actualizar la ventana en NodoD
    private synchronized void actualizarVentana() {
        List<JsonObject> inscripciones = cargarInscripciones();
        String ventanaActual = obtenerVentanaActual();
        List<JsonObject> nuevasInscripciones = new ArrayList<>();
    
        Iterator<JsonObject> iterator = inscripciones.iterator();
        while (iterator.hasNext()) {
            JsonObject inscripcion = iterator.next();
            if (inscripcion.get("ventana").getAsString().equals(ventanaActual)) {
                nuevasInscripciones.add(inscripcion);
                iterator.remove();
            }
        }
    
        guardarInscripciones(inscripciones);
        System.out.println("Ventana actualizada: " + ventanaActual);
    
        // Notificar a los NodosC
        notificarCambioVentana();
    }

    public void start() {
        try (ServerSocket serverSocket = new ServerSocket(puerto)) {
            System.out.println("Escuchando en el puerto " + puerto);

            while (true) {
                Socket clientSocket = serverSocket.accept();
                BufferedReader in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
                String receivedData = in.readLine();

                PrintWriter out = new PrintWriter(clientSocket.getOutputStream(), true);
                if ("CONSULTAR_INSCRIPCIONES".equals(receivedData)) {
                    out.println(obtenerInscripcionesActivas());
                } else {
                    JsonObject json = gson.fromJson(receivedData, JsonObject.class);
                    registrar(json.get("ip").getAsString(), json.get("puerto").getAsString(), json.get("horaRegistro").getAsString());
                    JsonObject respuesta = new JsonObject();
                    respuesta.addProperty("status", "OK");
                    respuesta.addProperty("message", "Nodo registrado para la ventana siguiente.");
                    out.println(gson.toJson(respuesta));
                }

                in.close();
                out.close();
                clientSocket.close();
            }
        } catch (IOException e) {
            System.err.println("Error en servidor: " + e.getMessage());
        }
    }

    public static void main(String[] args) {
        NodoD nodoD = new NodoD();
        nodoD.start();
    }
}