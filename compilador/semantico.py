"""
compilador/semantico.py
Fase 3: Análisis semántico.

Recibe el AST que construye el analizador sintáctico (parser.analizar), hace una
COPIA y la recorre aplicando las reglas semánticas del lenguaje:

    Declaración          -> inserción en la tabla de símbolos (dtype heredado)
    Uso de identificador -> búsqueda en la tabla de símbolos
    Expresión            -> obtención y propagación del tipo (atributo sintetizado)
    Asignación           -> comparación tipo del identificador vs. tipo de la expresión
    Condición            -> debe ser de tipo bool

Atributos que se anotan en cada nodo (clave "atributos"):
    dtype       heredado    tipo que la declaración transmite a sus identificadores
    tipo        sintetizado tipo de la expresión / identificador
    valor       sintetizado valor, solo si puede calcularse en compilación
    dir         dirección (desplazamiento) del identificador en la tabla
    conversion  conversión implícita aplicada al nodo (p. ej. "int→float")
    error       descripción del error semántico detectado en el nodo

Reglas de tipos:
    + - * / ^      int,int -> int · int,float / float,int / float,float -> float
                   ('/' entre enteros es división entera, como en C)
    %              solo int,int -> int
    < <= > >=      numéricos -> bool
    == !=          numéricos -> bool · bool,bool -> bool
    && || !        solo bool -> bool
    x++ x--        solo variables numéricas
    asignación     igual tipo, o int→float (conversión implícita permitida).
                   float→int es una conversión no válida.
    if/while/do/for la condición debe ser bool

Contrato (igual que lexer.py y parser.py):
    analizar(codigo_fuente: str) -> dict
        {"ast", "ast_anotado", "tabla_simbolos", "traza",
         "errores_lexicos", "errores_sintacticos", "errores_semanticos"}
    CLI:  python compilador/semantico.py <archivo>            -> JSON en stdout
          python compilador/semantico.py <archivo> --reporte  -> reporte de texto
"""

import sys
import os
import json
import copy
import math

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from parser import analizar as analizar_sintactico


# ══════════════════════════════════════════════════════════════════════════════
# Tipos y operadores
# ══════════════════════════════════════════════════════════════════════════════

INT, FLOAT, BOOL = "int", "float", "bool"
CADENA = "cadena"
ERROR = "error"          # tipo de una expresión que ya produjo un error (evita cascadas)

NUMERICOS = {INT, FLOAT}
TAMANOS = {INT: 4, FLOAT: 4, BOOL: 1}   # bytes por tipo, para la dirección de memoria

OP_ARITMETICOS = {"+", "-", "*", "/", "^"}
OP_RELACIONALES = {"<", "<=", ">", ">=", "==", "!="}
OP_IGUALDAD = {"==", "!="}
OP_LOGICOS = {"&&", "||"}

# Envoltorios del árbol extendido que solo contienen una expresión.
ENVOLTORIOS = {"SENT_EXPRESION", "SALIDA_EXPRESION"}

# Categorías de error semántico (las 7 que pide la fase + división entre cero).
E_NO_DECLARADO   = "Identificador no declarado"
E_DUPLICADO      = "Declaración duplicada"
E_INCOMPATIBLE   = "Incompatibilidad de tipos"
E_CONVERSION     = "Conversión no válida"
E_OPERADOR       = "Uso indebido de operador"
E_ASIGNACION     = "Asignación inconsistente"
E_CONDICION      = "Condición no booleana"
E_DIVISION_CERO  = "División entre cero"


# ══════════════════════════════════════════════════════════════════════════════
# Tabla de símbolos
# ══════════════════════════════════════════════════════════════════════════════

class TablaSimbolos:
    """
    Tabla de símbolos tipo diccionario: nombre -> entrada.

    El lenguaje solo tiene el bloque 'main { }', por lo que existe un único
    ámbito (global). Cada entrada guarda:
        nombre, tipo, ambito, direccion, tamano, valor,
        linea_declaracion, columna, lineas (todas las líneas donde aparece)
    """

    def __init__(self):
        self._entradas = {}
        self._siguiente_direccion = 0
        self.ambito = "global"

    def insertar(self, nombre, tipo, linea, columna):
        """Inserta un identificador. Devuelve la entrada, o None si ya existía."""
        if nombre in self._entradas:
            return None
        tamano = TAMANOS[tipo]
        entrada = {
            "nombre": nombre,
            "tipo": tipo,
            "ambito": self.ambito,
            "direccion": self._siguiente_direccion,
            "tamano": tamano,
            "valor": None,
            "linea_declaracion": linea,
            "columna": columna,
            "lineas": [linea],
        }
        self._siguiente_direccion += tamano
        self._entradas[nombre] = entrada
        return entrada

    def buscar(self, nombre):
        """Devuelve la entrada del identificador o None si no está declarado."""
        return self._entradas.get(nombre)

    def eliminar(self, nombre):
        """Elimina un identificador (se usaría al salir de un ámbito anidado)."""
        return self._entradas.pop(nombre, None)

    def registrar_linea(self, nombre, linea):
        """Agrega la línea a la lista de referencias del identificador."""
        entrada = self._entradas.get(nombre)
        if entrada is not None and linea:
            entrada["lineas"].append(linea)

    def valores(self):
        """Copia de los valores conocidos (para analizar ramas por separado)."""
        return {n: e["valor"] for n, e in self._entradas.items()}

    def restaurar_valores(self, valores):
        for nombre, valor in valores.items():
            if nombre in self._entradas:
                self._entradas[nombre]["valor"] = valor

    def entradas(self):
        return list(self._entradas.values())


# ══════════════════════════════════════════════════════════════════════════════
# Utilidades
# ══════════════════════════════════════════════════════════════════════════════

def formatear_valor(valor):
    """Representación legible de un valor calculado en compilación."""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float):
        texto = f"{valor:.6g}"
        if "." not in texto and "e" not in texto and "inf" not in texto:
            texto += ".0"
        return texto
    return str(valor)


def _division_entera(a, b):
    """División entera truncando hacia cero (como en C), sin pasar por float."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def _atributos(nodo):
    return nodo.setdefault("atributos", {})


def _desenvolver(nodo):
    """Salta los envoltorios SENT_EXPRESION / SALIDA_EXPRESION de un solo hijo."""
    while nodo is not None and nodo.get("type") in ENVOLTORIOS and len(nodo.get("children", [])) == 1:
        nodo = nodo["children"][0]
    return nodo


def _texto_expresion(nodo):
    """Reconstruye el texto de una expresión (para la traza y los mensajes)."""
    nodo = _desenvolver(nodo)
    if nodo is None:
        return ""
    tipo = nodo.get("type")
    if tipo == "OPERACION":
        partes = []
        for hijo in nodo["children"]:
            texto = _texto_expresion(hijo)
            if _desenvolver(hijo).get("type") == "OPERACION":
                texto = f"({texto})"
            partes.append(texto)
        return f" {nodo.get('value')} ".join(partes)
    if tipo == "COMPONENTE_UNARIO":
        op, operando = nodo["children"][0], nodo["children"][1]
        return f"{op.get('value')}{_texto_expresion(operando)}"
    return str(nodo.get("value", ""))


# ══════════════════════════════════════════════════════════════════════════════
# Analizador semántico
# ══════════════════════════════════════════════════════════════════════════════

class AnalizadorSemantico:

    def __init__(self):
        self.tabla = TablaSimbolos()
        self.errores = []
        self.traza = []

    # ── API ───────────────────────────────────────────────────────────────────
    def analizar(self, ast):
        """Devuelve una copia del AST con las anotaciones semánticas."""
        anotado = copy.deepcopy(ast)
        if anotado is not None:
            self._sentencia(anotado)
        return anotado

    # ── Registro de traza y errores ──────────────────────────────────────────
    def _traza(self, nodo, accion, detalle):
        self.traza.append({
            "linea": nodo.get("line") or 0,
            "accion": accion,
            "detalle": detalle,
        })

    def _error(self, nodo, categoria, descripcion):
        self.errores.append({
            "linea": nodo.get("line") or 0,
            "columna": nodo.get("column") or 0,
            "categoria": categoria,
            "descripcion": f"{categoria}: {descripcion}",
        })
        _atributos(nodo)["error"] = f"{categoria}: {descripcion}"
        self._traza(nodo, "ERROR", f"{categoria}: {descripcion}")

    # ── Tabla de símbolos: declaración y uso ─────────────────────────────────
    def _declarar(self, nodo_id, dtype):
        """Declaración -> inserción en la tabla (el ID hereda dtype)."""
        nombre = nodo_id.get("value")
        linea = nodo_id.get("line")
        _atributos(nodo_id)["dtype"] = dtype

        previa = self.tabla.buscar(nombre)
        if previa is not None:
            self._traza(nodo_id, "BUSCAR", f"'{nombre}' ya existe en la tabla ({previa['tipo']})")
            self._error(
                nodo_id, E_DUPLICADO,
                f"'{nombre}' ya fue declarado como {previa['tipo']} en la línea {previa['linea_declaracion']}",
            )
            self.tabla.registrar_linea(nombre, linea)
            return None

        entrada = self.tabla.insertar(nombre, dtype, linea, nodo_id.get("column"))
        _atributos(nodo_id)["dir"] = entrada["direccion"]
        self._traza(
            nodo_id, "INSERTAR",
            f"{nombre} : {dtype}  (dir {entrada['direccion']}, {entrada['tamano']} byte(s), dtype heredado)",
        )
        return entrada

    def _usar(self, nodo_id):
        """Uso de identificador -> búsqueda en la tabla."""
        nombre = nodo_id.get("value")
        entrada = self.tabla.buscar(nombre)
        if entrada is None:
            self._traza(nodo_id, "BUSCAR", f"'{nombre}' -> no encontrado")
            self._error(nodo_id, E_NO_DECLARADO, f"la variable '{nombre}' no ha sido declarada")
            _atributos(nodo_id)["tipo"] = ERROR
            return None

        self.tabla.registrar_linea(nombre, nodo_id.get("line"))
        attrs = _atributos(nodo_id)
        attrs["tipo"] = entrada["tipo"]
        attrs["dir"] = entrada["direccion"]
        self._traza(nodo_id, "BUSCAR", f"'{nombre}' -> {entrada['tipo']}, dir {entrada['direccion']}")
        return entrada

    # ── Sentencias ───────────────────────────────────────────────────────────
    def _sentencia(self, nodo):
        metodo = getattr(self, "_s_" + str(nodo.get("type")), None)
        if metodo is not None:
            metodo(nodo)
        else:
            for hijo in nodo.get("children", []):
                self._sentencia(hijo)

    def _s_ERROR_SINTACTICO(self, nodo):
        self._traza(nodo, "OMITIR", "sentencia con error sintáctico (no se analiza)")

    def _s_DECLARACION_VARIABLE(self, nodo):
        hijos = nodo["children"]
        nodo_tipo = hijos[0]
        dtype = nodo_tipo.get("value")
        # tipo -> int|float|bool : el tipo se sintetiza desde el token...
        _atributos(nodo_tipo)["tipo"] = dtype
        # ...y la declaración lo hereda hacia sus identificadores (dtype).
        _atributos(nodo)["dtype"] = dtype
        self._traza(nodo, "DECLARAR", f"tipo {dtype} -> dtype heredado a los identificadores")

        if nodo.get("value") == "=" and len(hijos) == 3:
            # int x = expresion;  -> la expresión se evalúa antes de declarar x
            nodo_id, expresion = hijos[1], hijos[2]
            tipo_expr = self._expresion(expresion)
            entrada = self._declarar(nodo_id, dtype)
            if entrada is not None:
                self._asignar(nodo, entrada, expresion, tipo_expr)
        else:
            for nodo_id in hijos[1:]:
                self._declarar(nodo_id, dtype)

    def _s_ASIGNACION(self, nodo):
        hijos = nodo["children"]
        nodo_id = hijos[0]
        lado_derecho = hijos[1] if len(hijos) > 1 else None
        expresion = _desenvolver(lado_derecho)

        # El lado derecho se evalúa primero; luego se busca el destino.
        tipo_expr = self._expresion(lado_derecho) if lado_derecho is not None else None
        entrada = self._usar(nodo_id)
        if entrada is None:
            _atributos(nodo)["tipo"] = ERROR
            return
        _atributos(nodo)["tipo"] = entrada["tipo"]

        if expresion is None or tipo_expr is None:
            # 'x = ;' : asignación vacía, no hay expresión que verificar.
            self._traza(nodo, "VERIFICAR", f"asignación vacía a '{entrada['nombre']}'")
            return
        self._asignar(nodo, entrada, expresion, tipo_expr)

    def _asignar(self, nodo, entrada, expresion, tipo_expr):
        """Compara el tipo del identificador con el de la expresión asignada."""
        nombre, destino = entrada["nombre"], entrada["tipo"]
        valor = _atributos(expresion).get("valor")

        if tipo_expr == ERROR:
            entrada["valor"] = None
            return

        if tipo_expr == destino:
            self._traza(nodo, "VERIFICAR", f"{nombre} ({destino}) = {tipo_expr}  ✓")
        elif destino == FLOAT and tipo_expr == INT:
            self._convertir(expresion, FLOAT, f"asignación a '{nombre}'")
            self._traza(nodo, "VERIFICAR", f"{nombre} (float) = int  ✓ con conversión int→float")
            if valor is not None:
                valor = float(valor)
        elif destino == INT and tipo_expr == FLOAT:
            self._error(
                nodo, E_CONVERSION,
                f"no se puede asignar un valor float a la variable int '{nombre}' (pérdida de precisión)",
            )
            entrada["valor"] = None
            return
        else:
            self._error(
                nodo, E_ASIGNACION,
                f"no se puede asignar un valor {tipo_expr} a la variable {destino} '{nombre}'",
            )
            entrada["valor"] = None
            return

        entrada["valor"] = valor
        if valor is not None:
            _atributos(nodo)["valor"] = valor
            self._traza(nodo, "ASIGNAR", f"{nombre} <- {formatear_valor(valor)}")
        else:
            self._traza(nodo, "ASIGNAR", f"{nombre} <- (valor conocido solo en ejecución)")

    def _s_INCREMENTO_OP(self, nodo):
        op = nodo.get("value")
        entrada = self._usar(nodo["children"][0])
        if entrada is None:
            return
        _atributos(nodo)["tipo"] = entrada["tipo"]
        if entrada["tipo"] not in NUMERICOS:
            self._error(
                nodo, E_OPERADOR,
                f"'{op}' requiere una variable numérica; '{entrada['nombre']}' es {entrada['tipo']}",
            )
            return
        if entrada["valor"] is not None:
            entrada["valor"] += 1 if op == "++" else -1
            _atributos(nodo)["valor"] = entrada["valor"]
            self._traza(nodo, "ASIGNAR", f"{entrada['nombre']}{op} -> {formatear_valor(entrada['valor'])}")
        else:
            self._traza(nodo, "ASIGNAR", f"{entrada['nombre']}{op}  ({entrada['tipo']} ✓)")

    def _s_SENT_IN(self, nodo):
        entrada = self._usar(nodo["children"][0])
        if entrada is not None:
            entrada["valor"] = None
            self._traza(nodo, "ASIGNAR", f"cin >> {entrada['nombre']}  (valor conocido solo en ejecución)")

    def _s_SENT_OUT(self, nodo):
        for hijo in nodo["children"]:
            self._expresion(hijo)

    # ── Estructuras de control ───────────────────────────────────────────────
    def _s_SELECCION(self, nodo):
        condicion, ramas = nodo["children"][0], nodo["children"][1:]
        self._condicion(condicion, "if")

        # Cada rama parte de los mismos valores; al salir, las variables que
        # alguna rama modifica dejan de tener un valor conocido.
        antes = self.tabla.valores()
        modificadas = set()
        for rama in ramas:
            self.tabla.restaurar_valores(antes)
            self._sentencia(rama)
            modificadas |= self._asignadas_en(rama)
        self.tabla.restaurar_valores(antes)
        self._invalidar(nodo, modificadas, "se modifica en una rama del if")

    def _s_ITERACION(self, nodo):
        condicion, cuerpo = nodo["children"][0], nodo["children"][1:]
        # El cuerpo se repite: sus variables no tienen valor fijo dentro del ciclo.
        modificadas = set()
        for parte in cuerpo:
            modificadas |= self._asignadas_en(parte)
        self._invalidar(nodo, modificadas, "se modifica dentro del while")
        self._condicion(condicion, "while")
        for parte in cuerpo:
            self._sentencia(parte)
        # El ciclo puede ejecutarse cero veces.
        self._invalidar(nodo, modificadas, registrar=False)

    def _s_REPETICION(self, nodo):
        cuerpo, condicion = nodo["children"][:-1], nodo["children"][-1]
        modificadas = set()
        for parte in cuerpo:
            modificadas |= self._asignadas_en(parte)
        self._invalidar(nodo, modificadas, "se modifica dentro del do-while")
        for parte in cuerpo:
            self._sentencia(parte)
        # El do-while se ejecuta al menos una vez: lo calculado en la última
        # vuelta del cuerpo sigue siendo válido después del ciclo.
        self._condicion(condicion, "do-while")

    def _s_CICLO_FOR(self, nodo):
        partes = {h.get("type"): h for h in nodo["children"]}
        inicializacion = partes.get("INICIALIZACION")
        condicion = partes.get("CONDICION")
        incremento = partes.get("INCREMENTO")
        cuerpo = partes.get("CUERPO")

        if inicializacion is not None:
            self._sentencia(inicializacion)

        modificadas = set()
        for parte in (incremento, cuerpo):
            if parte is not None:
                modificadas |= self._asignadas_en(parte)
        self._invalidar(nodo, modificadas, "se modifica dentro del for")

        if condicion is not None and condicion["children"]:
            self._condicion(condicion["children"][0], "for")
        if cuerpo is not None:
            self._sentencia(cuerpo)
        if incremento is not None:
            self._sentencia(incremento)
        self._invalidar(nodo, modificadas, registrar=False)

    def _condicion(self, expresion, estructura):
        tipo = self._expresion(expresion)
        nodo = _desenvolver(expresion)
        if tipo == BOOL:
            self._traza(nodo, "VERIFICAR", f"condición del {estructura}: bool  ✓")
        elif tipo not in (ERROR, None):
            self._error(
                nodo, E_CONDICION,
                f"la condición del {estructura} debe ser bool, se obtuvo {tipo} ({_texto_expresion(nodo)})",
            )

    def _asignadas_en(self, nodo):
        """Nombres de las variables que una sentencia (o bloque) modifica."""
        nombres = set()
        pila = [nodo]
        while pila:
            actual = pila.pop()
            if actual.get("type") in ("ASIGNACION", "INCREMENTO_OP", "SENT_IN") and actual.get("children"):
                nombres.add(actual["children"][0].get("value"))
            pila.extend(actual.get("children", []))
        return nombres

    def _invalidar(self, nodo, nombres, motivo="", registrar=True):
        """Las variables indicadas dejan de tener un valor conocido en compilación."""
        perdidos = []
        for nombre in sorted(nombres):
            entrada = self.tabla.buscar(nombre)
            if entrada is not None and entrada["valor"] is not None:
                entrada["valor"] = None
                perdidos.append(nombre)
        if perdidos and registrar:
            self._traza(nodo, "VALOR", f"{', '.join(perdidos)}: valor desconocido ({motivo})")

    # ── Expresiones (atributos sintetizados) ─────────────────────────────────
    def _expresion(self, nodo):
        """Calcula y anota el tipo (y el valor, si se puede) de una expresión."""
        if nodo is None:
            return None
        tipo_nodo = nodo.get("type")
        attrs = _atributos(nodo)

        if tipo_nodo in ENVOLTORIOS:
            if not nodo.get("children"):
                return None
            hijo = nodo["children"][0]
            tipo = self._expresion(hijo)
            attrs["tipo"] = tipo
            if "valor" in _atributos(hijo):
                attrs["valor"] = hijo["atributos"]["valor"]
            return tipo

        if tipo_nodo == "NUMERO":
            lexema = str(nodo.get("value"))
            if "." in lexema:
                attrs["tipo"], attrs["valor"] = FLOAT, float(lexema)
            else:
                attrs["tipo"], attrs["valor"] = INT, int(lexema)
            return attrs["tipo"]

        if tipo_nodo == "COMPONENTE_ID":
            entrada = self._usar(nodo)
            if entrada is None:
                return ERROR
            if entrada["valor"] is not None:
                attrs["valor"] = entrada["valor"]
            return entrada["tipo"]

        if tipo_nodo == "COMPONENTE_BOOL":
            attrs["tipo"] = BOOL
            return BOOL

        if tipo_nodo == "SALIDA_CADENA":
            attrs["tipo"] = CADENA
            return CADENA

        if tipo_nodo == "SALIDA_MIXTA":
            for hijo in nodo["children"]:
                self._expresion(hijo)
            attrs["tipo"] = CADENA
            return CADENA

        if tipo_nodo == "COMPONENTE_UNARIO":
            return self._unario(nodo)

        if tipo_nodo == "OPERACION":
            return self._binaria(nodo)

        for hijo in nodo.get("children", []):
            self._expresion(hijo)
        return None

    def _unario(self, nodo):
        attrs = _atributos(nodo)
        op = nodo["children"][0].get("value")
        operando = nodo["children"][1]
        tipo = self._expresion(operando)

        if tipo == ERROR:
            attrs["tipo"] = ERROR
        elif op != "!":
            self._error(nodo, E_OPERADOR, f"'{op}' es un operador binario, no puede usarse como unario")
            attrs["tipo"] = ERROR
        elif tipo != BOOL:
            self._error(nodo, E_OPERADOR, f"'!' requiere un operando bool, se recibió {tipo}")
            attrs["tipo"] = ERROR
        else:
            attrs["tipo"] = BOOL
            valor = _atributos(operando).get("valor")
            if valor is not None:
                attrs["valor"] = not valor
            self._traza(nodo, "TIPO", f"!{_texto_expresion(operando)} : bool")
        return attrs["tipo"]

    def _binaria(self, nodo):
        attrs = _atributos(nodo)
        op = nodo.get("value")
        izq, der = nodo["children"][0], nodo["children"][1]
        ti, td = self._expresion(izq), self._expresion(der)
        texto = f"{ti} {op} {td}"

        if ERROR in (ti, td) or None in (ti, td):
            attrs["tipo"] = ERROR
            return ERROR

        resultado = None
        if op in ("++", "--"):
            self._error(nodo, E_OPERADOR, f"'{op}' es un operador unario, no puede usarse entre dos operandos")
        elif op in OP_ARITMETICOS:
            if ti in NUMERICOS and td in NUMERICOS:
                resultado = self._promover(nodo, izq, ti, der, td)
            else:
                self._error(nodo, E_OPERADOR, f"'{op}' requiere operandos numéricos ({texto})")
        elif op == "%":
            if ti == INT and td == INT:
                resultado = INT
            else:
                self._error(nodo, E_OPERADOR, f"'%' solo admite operandos int ({texto})")
        elif op in OP_RELACIONALES:
            if ti in NUMERICOS and td in NUMERICOS:
                self._promover(nodo, izq, ti, der, td)
                resultado = BOOL
            elif ti == BOOL and td == BOOL:
                if op in OP_IGUALDAD:
                    resultado = BOOL
                else:
                    self._error(nodo, E_OPERADOR, f"'{op}' no está definido para operandos bool")
            else:
                self._error(nodo, E_INCOMPATIBLE, f"no se puede comparar {ti} con {td} usando '{op}'")
        elif op in OP_LOGICOS:
            if ti == BOOL and td == BOOL:
                resultado = BOOL
            else:
                self._error(nodo, E_OPERADOR, f"'{op}' requiere operandos bool ({texto})")

        if resultado is None:
            attrs["tipo"] = ERROR
            return ERROR

        attrs["tipo"] = resultado
        self._traza(nodo, "TIPO", f"{_texto_expresion(nodo)} : {texto} -> {resultado}")

        vi, vd = _atributos(izq).get("valor"), _atributos(der).get("valor")
        if op in ("/", "%") and vd is not None and vd == 0:
            self._error(nodo, E_DIVISION_CERO, f"'{_texto_expresion(nodo)}' divide entre cero")
        elif vi is not None and vd is not None:
            valor = self._plegar(op, vi, vd, resultado)
            if valor is not None:
                attrs["valor"] = valor
        return resultado

    def _promover(self, nodo, izq, ti, der, td):
        """Tipo resultante de dos numéricos; convierte el int a float si se mezclan."""
        if ti == td:
            return ti
        if ti == INT:
            self._convertir(izq, FLOAT, f"operador '{nodo.get('value')}'")
        else:
            self._convertir(der, FLOAT, f"operador '{nodo.get('value')}'")
        return FLOAT

    def _convertir(self, nodo, destino, contexto):
        nodo = _desenvolver(nodo)
        origen = _atributos(nodo).get("tipo")
        _atributos(nodo)["conversion"] = f"{origen}→{destino}"
        self._traza(
            nodo, "CONVERSIÓN",
            f"'{_texto_expresion(nodo)}' {origen}→{destino} en {contexto}",
        )

    def _plegar(self, op, a, b, tipo):
        """Valor de una operación entre constantes (None si no se puede calcular)."""
        try:
            if op == "+":
                r = a + b
            elif op == "-":
                r = a - b
            elif op == "*":
                r = a * b
            elif op == "/":
                r = _division_entera(a, b) if tipo == INT else a / b
            elif op == "%":
                r = a - b * _division_entera(a, b)
            elif op == "^":
                if tipo == INT and (b < 0 or b > 256):
                    return None
                r = a ** b
            elif op == "<":
                r = a < b
            elif op == "<=":
                r = a <= b
            elif op == ">":
                r = a > b
            elif op == ">=":
                r = a >= b
            elif op == "==":
                r = a == b
            elif op == "!=":
                r = a != b
            elif op == "&&":
                r = a and b
            elif op == "||":
                r = a or b
            else:
                return None
        except (OverflowError, ZeroDivisionError, ValueError):
            return None

        if isinstance(r, complex) or (isinstance(r, float) and not math.isfinite(r)):
            return None
        if tipo == FLOAT:
            return float(r)
        return r


# ══════════════════════════════════════════════════════════════════════════════
# API pública
# ══════════════════════════════════════════════════════════════════════════════

def analizar(codigo_fuente: str) -> dict:
    resultado = analizar_sintactico(codigo_fuente)
    ast = resultado.get("ast")

    analizador = AnalizadorSemantico()
    anotado = analizador.analizar(ast)

    return {
        "ast":                 ast,
        "ast_anotado":         anotado,
        "tabla_simbolos":      analizador.tabla.entradas(),
        "traza":               analizador.traza,
        "errores_lexicos":     resultado.get("errores_lexicos", []),
        "errores_sintacticos": resultado.get("errores_sintacticos", []),
        "errores_semanticos":  analizador.errores,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Reporte de texto (evidencia: árbol anotado, tabla de símbolos y errores)
# ══════════════════════════════════════════════════════════════════════════════

def _etiqueta_atributos(attrs):
    partes = []
    if "dtype" in attrs:
        partes.append(f"dtype={attrs['dtype']}↓")
    if attrs.get("tipo"):
        partes.append(f"tipo={attrs['tipo']}↑")
    if "valor" in attrs:
        partes.append(f"valor={formatear_valor(attrs['valor'])}↑")
    if "dir" in attrs:
        partes.append(f"dir={attrs['dir']}")
    if "conversion" in attrs:
        partes.append(f"conv {attrs['conversion']}")
    if "error" in attrs:
        partes.append("ERROR")
    return f"  [{', '.join(partes)}]" if partes else ""


def _arbol_texto(nodo, prefijo="", ultimo=True, raiz=True, lineas=None):
    if lineas is None:
        lineas = []
    if nodo is None:
        return lineas
    etiqueta = str(nodo.get("type"))
    if nodo.get("value") is not None:
        etiqueta += f" {nodo['value']}"
    if nodo.get("line"):
        etiqueta += f"  · L{nodo['line']}"
    etiqueta += _etiqueta_atributos(nodo.get("atributos", {}))

    if raiz:
        lineas.append(etiqueta)
        hijo_prefijo = ""
    else:
        lineas.append(f"{prefijo}{'└── ' if ultimo else '├── '}{etiqueta}")
        hijo_prefijo = prefijo + ("    " if ultimo else "│   ")

    hijos = nodo.get("children", [])
    for i, hijo in enumerate(hijos):
        _arbol_texto(hijo, hijo_prefijo, i == len(hijos) - 1, False, lineas)
    return lineas


def generar_reporte(resultado, ruta=None) -> str:
    salida = []
    titulo = "REPORTE DEL ANÁLISIS SEMÁNTICO"
    salida.append("=" * 78)
    salida.append(titulo + (f" — {os.path.basename(ruta)}" if ruta else ""))
    salida.append("=" * 78)
    salida.append("Atributos: ↑ sintetizado · ↓ heredado · conv = conversión implícita")
    salida.append("")

    salida.append("─" * 78)
    salida.append("1. ÁRBOL SINTÁCTICO CON ANOTACIONES SEMÁNTICAS")
    salida.append("─" * 78)
    if resultado.get("ast_anotado"):
        salida.extend(_arbol_texto(resultado["ast_anotado"]))
    else:
        salida.append("(no se pudo construir el árbol)")
    salida.append("")

    salida.append("─" * 78)
    salida.append("2. TABLA DE SÍMBOLOS")
    salida.append("─" * 78)
    encabezado = f"{'Nombre':<12}{'Tipo':<8}{'Dir':>5}{'Tam':>5}  {'Valor':<12}{'Ámbito':<9}{'Decl':>5}  Líneas"
    salida.append(encabezado)
    salida.append("-" * len(encabezado))
    for e in resultado.get("tabla_simbolos", []):
        valor = formatear_valor(e["valor"]) if e["valor"] is not None else "—"
        lineas = ", ".join(str(n) for n in e["lineas"])
        salida.append(
            f"{e['nombre']:<12}{e['tipo']:<8}{e['direccion']:>5}{e['tamano']:>5}  "
            f"{valor:<12}{e['ambito']:<9}{e['linea_declaracion']:>5}  {lineas}"
        )
    salida.append("")

    salida.append("─" * 78)
    salida.append("3. ERRORES")
    salida.append("─" * 78)
    total = 0
    for clave, nombre in (("errores_lexicos", "Léxico"),
                          ("errores_sintacticos", "Sintáctico"),
                          ("errores_semanticos", "Semántico")):
        for err in resultado.get(clave, []):
            total += 1
            salida.append(f"[{nombre}] L{err.get('linea', 0)}:C{err.get('columna', 0)}  {err.get('descripcion', '')}")
    if total == 0:
        salida.append("Sin errores ✓")
    salida.append("")

    salida.append("─" * 78)
    salida.append("4. RECORRIDO SEMÁNTICO")
    salida.append("─" * 78)
    for paso in resultado.get("traza", []):
        salida.append(f"L{paso['linea']:<4} {paso['accion']:<11} {paso['detalle']}")

    return "\n".join(salida)


# ══════════════════════════════════════════════════════════════════════════════
# Punto de entrada (CLI)
# ══════════════════════════════════════════════════════════════════════════════

def _resultado_vacio(descripcion):
    return {
        "ast": None, "ast_anotado": None, "tabla_simbolos": [], "traza": [],
        "errores_lexicos": [], "errores_sintacticos": [],
        "errores_semanticos": [{"linea": 0, "columna": 0, "categoria": "", "descripcion": descripcion}],
    }


if __name__ == "__main__":
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    modo_reporte = "--reporte" in sys.argv

    if not argumentos:
        resultado = _resultado_vacio("Uso: python compilador/semantico.py <archivo_fuente> [--reporte]")
        ruta = None
    else:
        ruta = argumentos[0]
        try:
            with open(ruta, encoding="utf-8") as f:
                resultado = analizar(f.read())
        except Exception as e:
            resultado = _resultado_vacio(f"Error al leer archivo: {e}")

    if modo_reporte:
        sys.stdout.reconfigure(encoding="utf-8")
        print(generar_reporte(resultado, ruta))
    else:
        # ensure_ascii: el JSON viaja por la tubería del subprocess sin depender
        # de la codificación de la consola (en Windows no es UTF-8).
        print(json.dumps(resultado, ensure_ascii=True, indent=2))
    sys.exit(0)
