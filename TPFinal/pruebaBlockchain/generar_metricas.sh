#!/bin/bash

# Número de repeticiones
N=1

# Archivo para guardar los tiempos
output_file="tiempos_minado00.txt"
> "$output_file"  # limpio archivo

for ((i=1; i<=N; i++)); do
    echo "Ejecución $i..."
    # Ejecutar el programa y capturar salida JSON final
    output=$(./MineroMD5CPU.exe genesis.json 0 -1 | tail -n 1)
    
    # Extraer elapsed_time_ms usando jq (herramienta para JSON)
    # Si no tienes jq, luego te digo cómo instalarlo
    tiempo=$(echo "$output" | jq '.elapsed_time_ms')

    echo "$tiempo" >> "$output_file"
done

# Calcular estadísticas básicas con awk
echo "Estadísticas de tiempo en ms para $N ejecuciones:"
awk '
{
    sum += $1;
    if (min == "" || $1 < min) min = $1;
    if (max == "" || $1 > max) max = $1;
    count++;
}
END {
    mean = sum / count;
    print "Promedio:", mean " ms";
    print "Mínimo:", min " ms";
    print "Máximo:", max " ms";
}' "$output_file"
