import com.google.gson.Gson;
import com.google.gson.JsonObject;

import java.io.*;
import java.net.*;
import java.time.*;
import java.time.format.DateTimeFormatter;

public class NodoC {
    private final int puertoLocal;
    private final String ipNodoD;
    private final int puertoNodoD;
    private static final Gson gson = new Gson();
    private static final ZoneId ZONA_ARGENTINA = ZoneId.of("America/Argentina/Buenos_Aires");

    public NodoC(String ipNodoD, int puertoNodoD) {
        this.puertoLocal = 10000 + (int)(Math.random() * 10000);
        this.ipNodoD = ipNodoD;
        this.puertoNodoD = puertoNodoD;
    }

    public void registrarEnNodoD() {
        try {
            JsonObject json = new JsonObject();
            json.addProperty("ip", InetAddress.getLocalHost().getHostAddress());
            json.addProperty("puerto", puertoLocal);
            json.addProperty("horaRegistro", LocalTime.now(ZONA_ARGENTINA).format(DateTimeFormatter.ofPattern("HH:mm:ss")));

            System.out.println("Enviando solicitud de inscripción a Nodo D: " + gson.toJson(json));

            Socket socket = new Socket(ipNodoD, puertoNodoD);
            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            out.println(gson.toJson(json));
            String response = in.readLine();
            System.out.println("Respuesta de Nodo D: " + response);
            JsonObject respuesta = gson.fromJson(response, JsonObject.class);
            if (respuesta.has("ventana_asignada")) {
                System.out.println("Nodo registrado para la ventana: " + respuesta.get("ventana_asignada").getAsString());
            }
            in.close();
            out.close();
            socket.close();
        } catch (Exception e) {
            System.err.println("Error registrando en D: " + e.getMessage());
        }
    }

    public void consultarInscripciones() {
        try {
            Socket socket = new Socket(ipNodoD, puertoNodoD);
            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            out.println("CONSULTAR_INSCRIPCIONES");
            String response = in.readLine();
            System.out.println("Inscripciones activas: " + response);
            in.close();
            out.close();
            socket.close();
        } catch (Exception e) {
            System.err.println("Error consultando inscripciones: " + e.getMessage());
        }
    }

    public void esperarVentana() {
        int intento = 0;
        int maxIntentos = 30; // Máximo de intentos de 30 (aproximadamente 5 minutos)
        int tiempoEspera = 10000; // Tiempo inicial de espera 10 segundos
    
        try {
            while (intento < maxIntentos) {
                String inscripcionesActivas = obtenerInscripcionesActivas();
                if (!inscripcionesActivas.isEmpty()) {
                    System.out.println("Inscripciones activas: " + inscripcionesActivas);
                    break;
                }
                
                System.out.println("Esperando ventana... Intento #" + (intento + 1));
    
                // Incrementamos el tiempo de espera entre intentos
                Thread.sleep(tiempoEspera);
                tiempoEspera += 5000; // Aumentar el tiempo de espera en 5 segundos cada vez
                intento++;
            }
    
            if (intento == maxIntentos) {
                System.out.println("No se han encontrado inscripciones activas después de " + maxIntentos + " intentos.");
            }
    
        } catch (InterruptedException e) {
            System.err.println("Error en el sleep: " + e.getMessage());
        }
    }
    
    public String obtenerInscripcionesActivas(){
        try{
            Socket socket = new Socket(ipNodoD, puertoNodoD);
            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            out.println("CONSULTAR_INSCRIPCIONES");
            String response = in.readLine();
            in.close();
            out.close();
            socket.close();
            return response;
        }catch (Exception e){
            System.err.println("Error consultando inscripciones: " + e.getMessage());
            return "";
        }
    }

    public void recibirNotificacionVentana() {
        try {
            ServerSocket serverSocket = new ServerSocket(puertoLocal);
            System.out.println("Esperando notificación de cambio de ventana...");
            Socket clientSocket = serverSocket.accept();
            BufferedReader in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
            
            String mensaje = in.readLine();
            JsonObject notificacion = gson.fromJson(mensaje, JsonObject.class);
            
            if (notificacion.has("mensaje")) {
                System.out.println("Notificación recibida: " + notificacion.get("mensaje").getAsString());
                
                // Enviar saludo de vuelta a NodoD
                String saludo = "¡Hola NodoD! Ventana actualizada correctamente.";
                PrintWriter out = new PrintWriter(clientSocket.getOutputStream(), true);
                out.println(saludo);
                System.out.println("Saludo enviado a NodoD: " + saludo);
                
                out.close();
            }
            
            in.close();
            clientSocket.close();
            serverSocket.close();
        } catch (IOException e) {
            System.err.println("Error en recibir notificación: " + e.getMessage());
        }
    }

    public static void main(String[] args) {
        if (args.length != 2) {
            System.out.println("Uso: java Nodo <IP Nodo D> <Puerto Nodo D>");
            return;
        }
        String ipNodoD = args[0];
        int puertoNodoD = Integer.parseInt(args[1]);
    
        NodoC nodo = new NodoC(ipNodoD, puertoNodoD);
        nodo.registrarEnNodoD();
        
        // Iniciar el hilo para recibir notificaciones
        new Thread(() -> nodo.recibirNotificacionVentana()).start();
        
        nodo.esperarVentana();
    }
}