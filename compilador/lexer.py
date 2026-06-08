"""
lexer.py — Analizador Léxico Autónomo
Materia: Compiladores 1

Uso desde terminal:
    python lexer.py <ruta_archivo_fuente>

Salida:
    JSON en stdout con la estructura:
    {
      "tokens": [ {"linea", "columna", "tipo", "lexema"}, ... ],
      "errores": [ {"linea", "columna", "descripcion"}, ... ]
    }

El lexer reconoce un lenguaje con sintaxis estilo C/C++.
"""

import sys
import re
import json


# ══════════════════════════════════════════════════════════════════════════════
# Definición de las palabras reservadas del lenguaje
# ══════════════════════════════════════════════════════════════════════════════

PALABRAS_RESERVADAS = {
    "if", "else", "end", "do", "while", "switch", "case",
    "int", "float", "main", "cin", "cout","for", "return"
}


# ══════════════════════════════════════════════════════════════════════════════
# Patrón maestro de expresiones regulares
# ══════════════════════════════════════════════════════════════════════════════
# Cada grupo nombrado ((?P<NOMBRE>...)) representa un tipo de token.
# El orden importa: los patrones más específicos van primero para evitar
# que un patrón genérico consuma un lexema que debería ser más específico.
# Ejemplo: "++" debe ir antes de "+", ">=" antes de ">".
# ══════════════════════════════════════════════════════════════════════════════

PATRON_MAESTRO = re.compile(r"""
    (?P<COMENTARIO_BLOQUE>/\*[\s\S]*?\*/)           |  # /* ... */ (multilínea)
    (?P<COMENTARIO_LINEA>//[^\n]*)                   |  # // hasta fin de línea
    (?P<NUMERO_REAL>\d+\.\d+)                        |  # 3.14  (real antes que entero)
    (?P<NUMERO_ENTERO>\d+)                           |  # 42
    (?P<CADENA>"[^"]*")                              |  # "texto"
    (?P<CARACTER>'[^']*')                            |  # 'c'
    (?P<IDENTIFICADOR>[a-zA-Z_][a-zA-Z0-9_]*)        |  # variables y palabras reservadas
    (?P<INCREMENTO>\+\+)                             |  # ++
    (?P<DECREMENTO>--)                               |  # --
    (?P<OP_AND>&&)                                   |  # and lógico
    (?P<OP_OR>\|\|)                                  |  # or lógico
    (?P<INSERCION><<)                               |  # << (inserción, cout)
    (?P<EXTRACCION>>>)                               |  # >> (extracción, cin)
    (?P<MENOR_IGUAL><=)                              |  # <=
    (?P<MAYOR_IGUAL>>=)                              |  # >=
    (?P<DIFERENTE>!=)                                |  # !=
    (?P<IGUAL_IGUAL>==)                              |  # ==
    (?P<ASIGNACION>=)                                |  # =
    (?P<NOT>!)                                       |  # not lógico
    (?P<MENOR><)                                     |  # <
    (?P<MAYOR>>)                                     |  # >
    (?P<SUMA>\+)                                     |  # +
    (?P<RESTA>-)                                     |  # -
    (?P<MULTIPLICACION>\*)                           |  # *
    (?P<DIVISION>/)                                  |  # /
    (?P<MODULO>%)                                    |  # %
    (?P<POTENCIA>\^)                                 |  # ^
    (?P<PARENTESIS_IZQ>\()                           |  # (
    (?P<PARENTESIS_DER>\))                           |  # )
    (?P<LLAVE_IZQ>\{)                                |  # {
    (?P<LLAVE_DER>\})                                |  # }
    (?P<COMA>,)                                      |  # ,
    (?P<PUNTO_Y_COMA>;)                              |  # ;
    (?P<DOS_PUNTOS>:)                                |  # : (case)
    (?P<ESPACIO>\s+)                                 |  # Espacios (se ignoran)
    (?P<ERROR>.)                                        # Cualquier otro carácter → error
""", re.VERBOSE)


# ══════════════════════════════════════════════════════════════════════════════
# Mapeo de nombres de grupo a tipos de token amigables
# ══════════════════════════════════════════════════════════════════════════════

MAPA_TIPOS = {
    "NUMERO_REAL":      "NUMERO_REAL",
    "NUMERO_ENTERO":    "NUMERO_ENTERO",
    "CADENA":           "CADENA",
    "CARACTER":         "CARACTER",
    "INCREMENTO":       "OP_ARITMETICO",
    "DECREMENTO":       "OP_ARITMETICO",
    "SUMA":             "OP_ARITMETICO",
    "RESTA":            "OP_ARITMETICO",
    "MULTIPLICACION":   "OP_ARITMETICO",
    "DIVISION":         "OP_ARITMETICO",
    "MODULO":           "OP_ARITMETICO",
    "POTENCIA":         "OP_ARITMETICO",
    "MENOR":            "OP_RELACIONAL",
    "MENOR_IGUAL":      "OP_RELACIONAL",
    "MAYOR":            "OP_RELACIONAL",
    "MAYOR_IGUAL":      "OP_RELACIONAL",
    "DIFERENTE":        "OP_RELACIONAL",
    "IGUAL_IGUAL":      "OP_RELACIONAL",
    "OP_AND":           "OP_LOGICO",
    "OP_OR":            "OP_LOGICO",
    "NOT":              "OP_LOGICO",
    "ASIGNACION":       "ASIGNACION",
    "PARENTESIS_IZQ":   "PARENTESIS_IZQ",
    "PARENTESIS_DER":   "PARENTESIS_DER",
    "LLAVE_IZQ":        "LLAVE_IZQ",
    "LLAVE_DER":        "LLAVE_DER",
    "COMA":             "COMA",
    "PUNTO_Y_COMA":     "PUNTO_Y_COMA",
    "DOS_PUNTOS":       "DOS_PUNTOS",
    "INSERCION":        "INSERCION",
    "EXTRACCION":       "EXTRACCION",
}


# ══════════════════════════════════════════════════════════════════════════════
# Función principal del análisis léxico
# ══════════════════════════════════════════════════════════════════════════════

def analizar(codigo_fuente: str) -> dict:
    """
    Recibe el código fuente como string y retorna un diccionario con:
      - "tokens":  lista de tokens reconocidos
      - "errores": lista de errores léxicos encontrados

    Cada token es: {"linea", "columna", "tipo", "lexema"}
    Cada error es: {"linea", "columna", "descripcion"}
    """
    tokens = []
    errores = []

    # Procesamos el código completo con finditer para mantener posiciones absolutas.
    # Luego calculamos línea y columna a partir de la posición absoluta.
    # Precalculamos los inicios de cada línea para búsquedas rápidas.
    inicios_linea = [0]
    for i, c in enumerate(codigo_fuente):
        if c == '\n':
            inicios_linea.append(i + 1)

    def pos_a_linea_columna(pos):
        """Convierte una posición absoluta a (línea, columna) base 1."""
        # Búsqueda binaria en inicios_linea
        lo, hi = 0, len(inicios_linea) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if inicios_linea[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        linea = lo + 1  # base 1
        columna = pos - inicios_linea[lo] + 1  # base 1
        return linea, columna

    for match in PATRON_MAESTRO.finditer(codigo_fuente):
        tipo = match.lastgroup   # Nombre del grupo que coincidió
        lexema = match.group()
        pos = match.start()
        linea, columna = pos_a_linea_columna(pos)

        # ── Ignorar espacios en blanco ────────────────────────────────────
        if tipo == "ESPACIO":
            continue

        # ── Ignorar comentarios (no se generan tokens) ───────────────────
        if tipo == "COMENTARIO_LINEA" or tipo == "COMENTARIO_BLOQUE":
            continue

        # ── Errores léxicos ──────────────────────────────────────────────
        if tipo == "ERROR":
            errores.append({
                "linea": linea,
                "columna": columna,
                "descripcion": f"Carácter inválido: '{lexema}'",
            })
            continue

        # ── Identificadores y Palabras Reservadas ────────────────────────
        if tipo == "IDENTIFICADOR":
            if lexema in PALABRAS_RESERVADAS:
                tipo_final = "PALABRA_RESERVADA"
            else:
                tipo_final = "IDENTIFICADOR"
        else:
            tipo_final = MAPA_TIPOS.get(tipo, tipo)

        tokens.append({
            "linea": linea,
            "columna": columna,
            "tipo": tipo_final,
            "lexema": lexema,
        })

    return {"tokens": tokens, "errores": errores}


# ══════════════════════════════════════════════════════════════════════════════
# Punto de entrada (ejecución autónoma desde terminal)
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print(
            json.dumps({
                "tokens": [],
                "errores": [{"linea": 0, "columna": 0, "descripcion": "Uso: python lexer.py <archivo_fuente>"}]
            }, ensure_ascii=False, indent=2)
        )
        sys.exit(1)

    ruta_archivo = sys.argv[1]

    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            codigo_fuente = f.read()
    except FileNotFoundError:
        print(
            json.dumps({
                "tokens": [],
                "errores": [{"linea": 0, "columna": 0, "descripcion": f"Archivo no encontrado: {ruta_archivo}"}]
            }, ensure_ascii=False, indent=2)
        )
        sys.exit(1)
    except Exception as e:
        print(
            json.dumps({
                "tokens": [],
                "errores": [{"linea": 0, "columna": 0, "descripcion": f"Error al leer archivo: {e}"}]
            }, ensure_ascii=False, indent=2)
        )
        sys.exit(1)

    resultado = analizar(codigo_fuente)

    # Imprimir JSON en stdout (canal de comunicación con el IDE)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


# ✅ implemented by agent — exportar_tokens added
def exportar_tokens(tokens: list, ruta: str):
    """Escribe los tokens en un archivo de texto en formato tabla."""
    with open(ruta, "w", encoding="utf-8") as f:
        for t in tokens:
            f.write(f"{t['tipo']}\t{t['lexema']}\t{t['linea']}\t{t['columna']}\n")

if __name__ == "__main__":
    main()
