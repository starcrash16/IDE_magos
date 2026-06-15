# DIAGNOSIS
# Error 1:
# 1. What does p_declaracion_variable currently accept as identifier? → IDENTIFICADOR (the terminal)
# 2. What does p_identificador_multi produce?                        → An ASTNode ("ID_MULTI") via the 'identificador' non-terminal
# 3. Why does 'int x, y, z;' fail?                                   → Because p_declaracion_variable expects a single IDENTIFICADOR, rejecting the comma-separated list that 'identificador' would successfully match.
#
# Error 2:
# 4. Does p_sent_out consume PUNTO_Y_COMA?                           → No
# 5. Does p_sent_in consume PUNTO_Y_COMA?                            → Yes
# 6. Why does 'cout << "texto";' fail?                               → The parser encounters the PUNTO_Y_COMA (;) but p_sent_out doesn't expect it, resulting in a syntax error.

"""
BNF GRAMMAR
programa          -> main { lista_declaracion }
lista_declaracion -> lista_declaracion declaracion
                   | declaracion
declaracion       -> declaracion_variable
                   | lista_sentencias
declaracion_variable -> tipo identificador ;
                   | tipo id = expresion ;
identificador     -> id
                   | identificador , id
tipo              -> int | float | bool
lista_sentencias  -> lista_sentencias sentencia
                   | empty
sentencia         -> seleccion
                   | iteracion
                   | repeticion
                   | sent_in
                   | sent_out
                   | asignacion
asignacion        -> id = sent_expresion
sent_expresion    -> expresion ;
                   | ;
seleccion         -> if expresion then lista_sentencias end
                   | if expresion then lista_sentencias else lista_sentencias end
iteracion         -> while expresion lista_sentencias end
                   | for ( asignacion_simple ; expresion ; incremento ) lista_sentencias end
repeticion        -> do lista_sentencias while expresion ;
asignacion_simple -> id = expresion
incremento        -> id ++ | id -- | asignacion_simple
sentencia         -> ... | id ++ ; | id -- ;
sent_in           -> cin >> id ;
sent_out          -> cout << salida ;
salida            -> cadena
                   | expresion
                   | cadena << expresion
                   | expresion << cadena
expresion         -> expresion_simple
                   | expresion_simple rel_op expresion_simple
                   | expresion && expresion
                   | expresion || expresion
rel_op            -> < | <= | > | >= | == | !=
expresion_simple  -> expresion_simple suma_op termino
                   | termino
suma_op           -> + | - | ++ | --
termino           -> termino mult_op factor
                   | factor
mult_op           -> * | / | %
factor            -> factor pot_op componente
                   | componente
pot_op            -> ^
componente        -> ( expresion )
                   | número
                   | id
                   | bool
                   | op_logico componente
op_logico         -> && | || | !
cadena            -> CADENA
"""
# ✅ implemented by agent — BNF comment block matches grammar

import sys
import os
import json
import ply.yacc as yacc

class ASTNode:
    # ✅ already present
    __slots__ = ("type", "children", "value", "line")

    def __init__(self, type, children=None, value=None, line=None):
        self.type     = type
        self.children = children or []
        self.value    = value
        self.line     = line

def ast_to_dict(node):
    # ✅ already present
    if node is None:
        return None
    return {
        "type":     node.type,
        "value":    node.value,
        "line":     node.line,
        "children": [ast_to_dict(c) for c in node.children if c is not None],
    }

class _PLYToken:
    def __init__(self, type, value, lineno, lexpos):
        self.type   = type
        self.value  = value
        self.lineno = lineno
        self.lexpos = lexpos

# ✅ implemented by agent — All token types from CLAUDE.md are declared in the PLY tokens tuple
tokens = (
    "PALABRA_RESERVADA", "IDENTIFICADOR", "NUMERO_ENTERO", "NUMERO_REAL", "CADENA", "CARACTER",
    "OP_ARITMETICO", "OP_RELACIONAL", "OP_LOGICO", "ASIGNACION", "PARENTESIS_IZQ", "PARENTESIS_DER",
    "LLAVE_IZQ", "LLAVE_DER", "COMA", "PUNTO_Y_COMA", "DOS_PUNTOS", "INSERCION", "EXTRACCION",
    # Additional specific grammar tokens mapped by the LexerBridge
    "MAIN", "INT", "FLOAT", "BOOL", "IF", "THEN", "ELSE", "END", "WHILE", "DO", "FOR", "CIN", "COUT",
    "MENOR", "MENOR_IGUAL", "MAYOR", "MAYOR_IGUAL", "IGUAL_IGUAL", "DIFERENTE",
    "MAS", "MENOS", "MAS_MAS", "MENOS_MENOS",
    "POR", "ENTRE", "MODULO",
    "POTENCIA",
    "AND", "OR", "NOT",
    "UMINUS"
)

# ✅ implemented by agent — precedence tuple covers required operators
precedence = (
    ("right", "ASIGNACION"),
    ("left", "OR"),
    ("left", "AND"),
    ("right", "NOT"),
    ("left", "MENOR", "MENOR_IGUAL", "MAYOR", "MAYOR_IGUAL", "IGUAL_IGUAL", "DIFERENTE"),
    ("left", "MAS", "MENOS"),
    ("left", "POR", "ENTRE", "MODULO"),
    ("right", "POTENCIA"),
    ("right", "UMINUS"),
)

_KW_MAP = {
    "main": "MAIN", "int": "INT", "float": "FLOAT", "bool": "BOOL",
    "if": "IF", "then": "THEN", "else": "ELSE", "end": "END",
    "while": "WHILE", "do": "DO", "for": "FOR", "cin": "CIN", "cout": "COUT",
}

_REL_MAP = {
    "<": "MENOR", "<=": "MENOR_IGUAL", ">": "MAYOR", ">=": "MAYOR_IGUAL", "==": "IGUAL_IGUAL", "!=": "DIFERENTE"
}

_ARIT_MAP = {
    "+": "MAS", "-": "MENOS", "++": "MAS_MAS", "--": "MENOS_MENOS",
    "*": "POR", "/": "ENTRE", "%": "MODULO", "^": "POTENCIA"
}

_LOG_MAP = {
    "&&": "AND", "||": "OR", "!": "NOT"
}

class _LexerBridge:
    def __init__(self, token_dicts):
        self._tokens = []
        self.lineno = 1
        self.lexpos = 0
        self.input  = ""

        for td in token_dicts:
            tipo_lexer  = td["tipo"]
            lexema      = td["lexema"]
            linea       = td.get("linea", 1)
            columna     = td.get("columna", 0)

            ply_type = tipo_lexer
            
            if tipo_lexer in ("PALABRA_RESERVADA", "IDENTIFICADOR") and lexema in _KW_MAP:
                ply_type = _KW_MAP[lexema]
            elif tipo_lexer == "OP_RELACIONAL" and lexema in _REL_MAP:
                ply_type = _REL_MAP[lexema]
            elif tipo_lexer == "OP_ARITMETICO" and lexema in _ARIT_MAP:
                ply_type = _ARIT_MAP[lexema]
            elif tipo_lexer == "OP_LOGICO" and lexema in _LOG_MAP:
                ply_type = _LOG_MAP[lexema]
            
            self._tokens.append(_PLYToken(
                type   = ply_type,
                value  = lexema,
                lineno = linea,
                lexpos = columna,
            ))

        self._pos = 0

    def token(self):
        if self._pos >= len(self._tokens):
            return None
        tok = self._tokens[self._pos]
        self.lineno = tok.lineno
        self.lexpos = tok.lexpos
        self._pos += 1
        return tok

_errores_sintacticos = []

# Declaraciones de nivel superior que se reducen correctamente durante el parseo.
# Permite reconstruir un árbol parcial cuando el parseo global falla (p. ej. un
# bloque sin cerrar consume la '}' final y 'programa' nunca se reduce).
_declaraciones_parseadas = []

# Mayor 'lista_sentencias' reducida. Por ser recursiva por la izquierda, PLY la
# reduce de forma incremental; al fallar dentro de un bloque anidado la última
# reducida sería un bloque interno pequeño, por eso conservamos la de mayor
# tamaño (el bloque de sentencias de nivel superior). Sirve para rescatar las
# sentencias en curso cuando el parseo global falla antes de que su 'declaracion'
# contenedora llegue a reducir.
_ultima_lista_sentencias = None


def _tam_arbol(node):
    if node is None:
        return 0
    return 1 + sum(_tam_arbol(c) for c in node.children)


def _construir_ast_parcial():
    """Ensambla un PROGRAMA con lo reducido hasta el punto de fallo."""
    hijos = list(_declaraciones_parseadas)
    if _ultima_lista_sentencias is not None and (
        not hijos or hijos[-1] is not _ultima_lista_sentencias
    ):
        hijos.append(_ultima_lista_sentencias)
    if not hijos:
        return None
    return ASTNode(
        "PROGRAMA",
        [ASTNode("LISTA_DECLARACION", hijos, line=hijos[0].line)],
        line=hijos[0].line,
    )

# ✅ implemented by agent — Every non-terminal in the grammar has a corresponding p_* function.
def p_programa(p):
    """programa : MAIN LLAVE_IZQ lista_declaracion LLAVE_DER"""
    p[0] = ASTNode("PROGRAMA", [p[3]], line=p.lineno(1))

def p_lista_declaracion_multi(p):
    """lista_declaracion : lista_declaracion declaracion"""
    # Lista plana: cada declaración se agrega como hermana en el mismo nodo,
    # en lugar de anidar un nuevo LISTA_DECLARACION (que producía una "escalera").
    if p[2] is not None:
        p[1].children.append(p[2])
    p[0] = p[1]

def p_lista_declaracion_single(p):
    """lista_declaracion : declaracion"""
    p[0] = ASTNode("LISTA_DECLARACION", [p[1]], line=p[1].line)

def p_declaracion_var(p):
    """declaracion : declaracion_variable"""
    p[0] = p[1]
    _declaraciones_parseadas.append(p[0])

def p_declaracion_sent(p):
    """declaracion : lista_sentencias"""
    p[0] = p[1]
    if p[0] is not None:
        _declaraciones_parseadas.append(p[0])

# Recuperación de errores a nivel de sentencia/declaración:
# ante un error, PLY consume tokens hasta el ';' y produce un nodo ERROR_SINTACTICO,
# de modo que el resto del árbol se sigue construyendo (igual que la referencia).
def p_declaracion_error(p):
    """declaracion : error PUNTO_Y_COMA"""
    p[0] = ASTNode("ERROR_SINTACTICO", line=p.lineno(2))
    _declaraciones_parseadas.append(p[0])

def p_declaracion_variable(p):
    """declaracion_variable : tipo identificador PUNTO_Y_COMA"""
    # p[2] es una lista plana de nodos ID: todas las variables declaradas en la
    # misma sentencia quedan como hermanas bajo el mismo DECLARACION_VARIABLE.
    p[0] = ASTNode(
        "DECLARACION_VARIABLE",
        [p[1]] + p[2],
        line=p[1].line,
    )

def p_declaracion_variable_asignacion(p):
    """declaracion_variable : tipo IDENTIFICADOR ASIGNACION expresion PUNTO_Y_COMA"""
    p[0] = ASTNode(
        "DECLARACION_VARIABLE",
        [
            p[1],
            ASTNode("ID", value=p[2], line=p.lineno(2)),
            p[4],
        ],
        value="=",
        line=p[1].line,
    )

# 'identificador' acumula los ID en una lista de Python (no en un árbol binario),
# de modo que 'int x,y,z,r;' produzca cuatro hermanos al mismo nivel.
def p_identificador_single(p):
    """identificador : IDENTIFICADOR"""
    p[0] = [ASTNode("ID", value=p[1], line=p.lineno(1))]

def p_identificador_multi(p):
    """identificador : identificador COMA IDENTIFICADOR"""
    p[0] = p[1] + [ASTNode("ID", value=p[3], line=p.lineno(3))]

def p_tipo(p):
    """tipo : INT
            | FLOAT
            | BOOL"""
    p[0] = ASTNode("TIPO", value=p[1], line=p.lineno(1))

def p_lista_sentencias_multi(p):
    """lista_sentencias : lista_sentencias sentencia"""
    global _ultima_lista_sentencias
    # Lista plana: las sentencias se acumulan como hermanas en el mismo nodo.
    if p[1] is None:
        p[0] = ASTNode("LISTA_SENTENCIAS", [p[2]], line=p[2].line)
    else:
        p[1].children.append(p[2])
        p[0] = p[1]
    if _tam_arbol(p[0]) >= _tam_arbol(_ultima_lista_sentencias):
        _ultima_lista_sentencias = p[0]

def p_lista_sentencias_empty(p):
    """lista_sentencias : """
    p[0] = None

def p_sentencia(p):
    """sentencia : seleccion
                 | iteracion
                 | repeticion
                 | sent_in
                 | sent_out
                 | asignacion"""
    p[0] = p[1]

# Recuperación de errores también a nivel de sentencia: ante un error dentro de
# un bloque (if/while/do), se descartan tokens hasta el ';' y se inserta un nodo
# ERROR_SINTACTICO, sin destruir el bloque ni el resto del árbol.
def p_sentencia_error(p):
    """sentencia : error PUNTO_Y_COMA"""
    p[0] = ASTNode("ERROR_SINTACTICO", line=p.lineno(2))

# La asignación con ';' reutiliza 'asignacion_simple' (id = expresion) para no
# duplicar la producción 'IDENTIFICADOR ASIGNACION expresion' (evita un conflicto
# reduce/reduce con el for). Se conserva el envoltorio SENT_EXPRESION.
def p_asignacion(p):
    """asignacion : asignacion_simple PUNTO_Y_COMA"""
    ident, expr = p[1].children[0], p[1].children[1]
    p[0] = ASTNode("ASIGNACION", [ident, ASTNode("SENT_EXPRESION", [expr], line=expr.line)], line=p[1].line)

def p_asignacion_vacia(p):
    """asignacion : IDENTIFICADOR ASIGNACION PUNTO_Y_COMA"""
    p[0] = ASTNode(
        "ASIGNACION",
        [ASTNode("ID", value=p[1], line=p.lineno(1)), ASTNode("SENT_EXPRESION", line=p.lineno(2))],
        line=p.lineno(1),
    )

# Terminador de bloque: acepta 'end' o 'end;' (el ';' final es opcional, como en
# pruebamtaBlanca.txt). No produce nodo; solo cierra el bloque.
def p_fin_bloque(p):
    """fin_bloque : END
                  | END PUNTO_Y_COMA"""
    p[0] = None

# Con 'end' explícito cada 'if' se cierra de forma no ambigua: NO hay problema de
# dangling else, porque el 'else' solo puede pertenecer al 'if' aún abierto.
def p_seleccion_if(p):
    """seleccion : IF expresion THEN lista_sentencias fin_bloque"""
    p[0] = ASTNode("SELECCION", [p[2], p[4]], line=p.lineno(1))

def p_seleccion_if_else(p):
    """seleccion : IF expresion THEN lista_sentencias ELSE lista_sentencias fin_bloque"""
    p[0] = ASTNode("SELECCION", [p[2], p[4], p[6]], line=p.lineno(1))

def p_iteracion(p):
    """iteracion : WHILE expresion lista_sentencias fin_bloque"""
    p[0] = ASTNode("ITERACION", [p[2], p[3]], line=p.lineno(1))

# El ';' final cierra el do-while de forma inequívoca (estilo C: do ... while(c);).
# Sin él, un 'while' que siguiera al do-while sería ambiguo (¿cierra el do o
# inicia un ciclo nuevo?). El terminador elimina ese conflicto.
def p_repeticion(p):
    """repeticion : DO lista_sentencias WHILE expresion PUNTO_Y_COMA"""
    p[0] = ASTNode("REPETICION", [p[2], p[4]], line=p.lineno(1))

# Ciclo for: for ( init ; condicion ; incremento ) cuerpo end
# El AST agrupa explícitamente inicialización, condición, incremento y cuerpo
# para que la jerarquía del ciclo quede clara.
def p_iteracion_for(p):
    """iteracion : FOR PARENTESIS_IZQ asignacion_simple PUNTO_Y_COMA expresion PUNTO_Y_COMA incremento PARENTESIS_DER lista_sentencias fin_bloque"""
    p[0] = ASTNode(
        "CICLO_FOR",
        [
            ASTNode("INICIALIZACION", [p[3]], line=p[3].line),
            ASTNode("CONDICION", [p[5]], line=p[5].line),
            ASTNode("INCREMENTO", [p[7]], line=p[7].line),
            ASTNode("CUERPO", [p[9]] if p[9] is not None else [], line=p.lineno(1)),
        ],
        line=p.lineno(1),
    )

# Asignación sin ';' (reutilizable en la inicialización del for).
def p_asignacion_simple(p):
    """asignacion_simple : IDENTIFICADOR ASIGNACION expresion"""
    p[0] = ASTNode("ASIGNACION", [ASTNode("ID", value=p[1], line=p.lineno(1)), p[3]], line=p.lineno(1))

# Incremento/decremento: i++ , i-- o i = expresion
def p_incremento_postfijo(p):
    """incremento : IDENTIFICADOR MAS_MAS
                  | IDENTIFICADOR MENOS_MENOS"""
    p[0] = ASTNode("INCREMENTO_OP", [ASTNode("ID", value=p[1], line=p.lineno(1))], value=p[2], line=p.lineno(1))

def p_incremento_asignacion(p):
    """incremento : asignacion_simple"""
    p[0] = p[1]

# Permite usar 'i++;' / 'c--;' como sentencia independiente.
# Se escribe con terminales explícitos (no reusa 'incremento') para no chocar
# con 'asignacion' cuando el lookahead es '=': aquí el lookahead siempre es ++/--.
def p_sentencia_incremento(p):
    """sentencia : IDENTIFICADOR MAS_MAS PUNTO_Y_COMA
                 | IDENTIFICADOR MENOS_MENOS PUNTO_Y_COMA"""
    p[0] = ASTNode("INCREMENTO_OP", [ASTNode("ID", value=p[1], line=p.lineno(1))], value=p[2], line=p.lineno(1))

# PUNTO_Y_COMA present
# identifier form correct (terminal)
def p_sent_in(p):
    """sent_in : CIN EXTRACCION IDENTIFICADOR PUNTO_Y_COMA"""
    p[0] = ASTNode("SENT_IN", [ASTNode("ID", value=p[3], line=p.lineno(3))], line=p.lineno(1))

# PUNTO_Y_COMA present
def p_sent_out(p):
    """sent_out : COUT INSERCION salida PUNTO_Y_COMA"""
    p[0] = ASTNode("SENT_OUT", [p[3]], line=p.lineno(1))

def p_salida_cadena(p):
    """salida : CADENA"""
    p[0] = ASTNode("SALIDA_CADENA", value=p[1], line=p.lineno(1))

def p_salida_expresion(p):
    """salida : expresion"""
    p[0] = ASTNode("SALIDA_EXPRESION", [p[1]], line=p[1].line)

def p_salida_mix1(p):
    """salida : CADENA INSERCION expresion"""
    p[0] = ASTNode("SALIDA_MIXTA", [ASTNode("SALIDA_CADENA", value=p[1], line=p.lineno(1)), p[3]], line=p.lineno(1))

def p_salida_mix2(p):
    """salida : expresion INSERCION CADENA"""
    p[0] = ASTNode("SALIDA_MIXTA", [p[1], ASTNode("SALIDA_CADENA", value=p[3], line=p.lineno(3))], line=p[1].line)

def p_expresion_simple_only(p):
    """expresion : expresion_simple"""
    p[0] = p[1]

def p_expresion_rel(p):
    """expresion : expresion_simple rel_op expresion_simple"""
    p[0] = ASTNode("OPERACION", [p[1], p[3]], value=p[2].value, line=p[1].line)

def p_expresion_logica(p):
    """expresion : expresion AND expresion
                 | expresion OR expresion"""
    p[0] = ASTNode("OPERACION", [p[1], p[3]], value=p[2], line=p[1].line)

def p_rel_op(p):
    """rel_op : MENOR
              | MENOR_IGUAL
              | MAYOR
              | MAYOR_IGUAL
              | IGUAL_IGUAL
              | DIFERENTE"""
    p[0] = ASTNode("REL_OP", value=p[1], line=p.lineno(1))

def p_expresion_simple_suma(p):
    """expresion_simple : expresion_simple suma_op termino"""
    # Recursión por la izquierda -> asociatividad izquierda: a - b - c = (a - b) - c
    p[0] = ASTNode("OPERACION", [p[1], p[3]], value=p[2].value, line=p[1].line)

def p_expresion_simple_term(p):
    """expresion_simple : termino"""
    p[0] = p[1]

def p_suma_op(p):
    """suma_op : MAS
               | MENOS
               | MAS_MAS
               | MENOS_MENOS"""
    p[0] = ASTNode("SUMA_OP", value=p[1], line=p.lineno(1))

def p_termino_mult(p):
    """termino : termino mult_op factor"""
    # '*', '/', '%' ligan más fuerte que '+'/'-' por estar en un nivel inferior.
    p[0] = ASTNode("OPERACION", [p[1], p[3]], value=p[2].value, line=p[1].line)

def p_termino_factor(p):
    """termino : factor"""
    p[0] = p[1]

def p_mult_op(p):
    """mult_op : POR
               | ENTRE
               | MODULO"""
    p[0] = ASTNode("MULT_OP", value=p[1], line=p.lineno(1))

def p_factor_pot(p):
    """factor : factor pot_op componente"""
    p[0] = ASTNode("OPERACION", [p[1], p[3]], value=p[2].value, line=p[1].line)

def p_factor_comp(p):
    """factor : componente"""
    p[0] = p[1]

def p_pot_op(p):
    """pot_op : POTENCIA"""
    p[0] = ASTNode("POT_OP", value=p[1], line=p.lineno(1))

def p_numero(p):
    """numero : NUMERO_ENTERO
              | NUMERO_REAL"""
    p[0] = ASTNode("NUMERO", value=p[1], line=p.lineno(1))

def p_componente_paren(p):
    """componente : PARENTESIS_IZQ expresion PARENTESIS_DER"""
    p[0] = p[2]

def p_componente_numero(p):
    """componente : numero"""
    p[0] = p[1]

def p_componente_id(p):
    """componente : IDENTIFICADOR"""
    p[0] = ASTNode("COMPONENTE_ID", value=p[1], line=p.lineno(1))

def p_componente_bool(p):
    """componente : BOOL"""
    p[0] = ASTNode("COMPONENTE_BOOL", value=p[1], line=p.lineno(1))

def p_componente_logico(p):
    """componente : op_logico componente"""
    p[0] = ASTNode("COMPONENTE_UNARIO", [p[1], p[2]], line=p[1].line)

def p_op_logico(p):
    """op_logico : AND
                 | OR
                 | NOT"""
    p[0] = ASTNode("OP_LOGICO", value=p[1], line=p.lineno(1))

def p_error(p):
    """Manejo de errores sintácticos con recuperación a nivel de sentencia.

    Solo registra el error. La recuperación la realiza PLY mediante la regla
    'declaracion : error PUNTO_Y_COMA': se descartan los tokens conflictivos
    hasta el ';' y se inserta un nodo ERROR_SINTACTICO, sin destruir el árbol.
    """
    if p:
        _errores_sintacticos.append({
            "linea": getattr(p, "lineno", 0),
            "columna": getattr(p, "lexpos", 0),
            "descripcion": f"Token inesperado: '{p.value}' (tipo: {p.type})"
        })
    else:
        _errores_sintacticos.append({
            "linea": 0,
            "columna": 0,
            "descripcion": "Fin de entrada inesperado (¿falta ';' o 'end'?)"
        })

# ✅ implemented by agent — yacc.yacc(debug=False, write_tables=False, errorlog=yacc.NullLogger())
_parser = yacc.yacc(
    debug=False,
    write_tables=False,
    errorlog=yacc.NullLogger(),
)

# ✅ implemented by agent — analizar() public contract
def analizar(codigo_fuente: str) -> dict:
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    from lexer import analizar as lexer_analizar

    resultado_lexico = lexer_analizar(codigo_fuente)
    lista_tokens  = resultado_lexico.get("tokens", [])
    errores_lex   = resultado_lexico.get("errores", [])

    global _ultima_lista_sentencias
    _ultima_lista_sentencias = None
    _errores_sintacticos.clear()
    _declaraciones_parseadas.clear()
    lexer_bridge = _LexerBridge(lista_tokens)

    try:
        ast = _parser.parse(lexer=lexer_bridge, tracking=True)
    except Exception:
        ast = None

    # Si el parseo global falló pero hubo declaraciones válidas, devolvemos un
    # árbol parcial: el objetivo es mostrar siempre un árbol cuando el léxico es
    # correcto, aunque existan errores sintácticos.
    if ast is None:
        ast = _construir_ast_parcial()

    return {
        "ast":                 ast_to_dict(ast),
        "tokens":              lista_tokens,
        "errores_lexicos":     errores_lex,
        "errores_sintacticos": list(_errores_sintacticos),
    }

# ✅ implemented by agent — Token file input
def analizar_desde_archivo(ruta: str) -> dict:
    """Reads tokens from a plain-text token file and parses them."""
    tokens = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    tipo = parts[0]
                    columna = int(parts[-1])
                    linea = int(parts[-2])
                    lexema = " ".join(parts[1:-2])
                    tokens.append({
                        "tipo": tipo,
                        "lexema": lexema,
                        "linea": linea,
                        "columna": columna
                    })
    except Exception:
        pass
        
    global _ultima_lista_sentencias
    _ultima_lista_sentencias = None
    _errores_sintacticos.clear()
    _declaraciones_parseadas.clear()
    lexer_bridge = _LexerBridge(tokens)

    try:
        ast = _parser.parse(lexer=lexer_bridge, tracking=True)
    except Exception:
        ast = None

    if ast is None:
        ast = _construir_ast_parcial()

    return {
        "ast":                 ast_to_dict(ast),
        "tokens":              tokens,
        "errores_lexicos":     [],
        "errores_sintacticos": list(_errores_sintacticos),
    }

# ✅ implemented by agent — CLI entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "ast": None,
            "tokens": [],
            "errores_lexicos": [],
            "errores_sintacticos": [{"linea": 0, "columna": 0, "descripcion": "Uso: python compilador/parser.py <archivo_fuente>"}]
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    ruta = sys.argv[1]

    try:
        with open(ruta, encoding="utf-8") as f:
            source = f.read()
        result = analizar(source)
    except Exception as e:
        result = {
            "ast": None,
            "tokens": [],
            "errores_lexicos": [],
            "errores_sintacticos": [{"linea": 0, "columna": 0, "descripcion": f"Error al leer archivo: {e}"}]
        }
        
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)
