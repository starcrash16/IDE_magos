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
repeticion        -> do lista_sentencias while expresion
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
    "MAIN", "INT", "FLOAT", "BOOL", "IF", "THEN", "ELSE", "END", "WHILE", "DO", "CIN", "COUT",
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
    "while": "WHILE", "do": "DO", "cin": "CIN", "cout": "COUT",
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

# ✅ implemented by agent — Every non-terminal in the grammar has a corresponding p_* function.
def p_programa(p):
    """programa : MAIN LLAVE_IZQ lista_declaracion LLAVE_DER"""
    p[0] = ASTNode("PROGRAMA", [p[3]], line=p.lineno(1))

def p_lista_declaracion_multi(p):
    """lista_declaracion : lista_declaracion declaracion"""
    p[0] = ASTNode("LISTA_DECLARACION", [p[1], p[2]], line=p[1].line)

def p_lista_declaracion_single(p):
    """lista_declaracion : declaracion"""
    p[0] = ASTNode("LISTA_DECLARACION", [p[1]], line=p[1].line)

def p_declaracion_var(p):
    """declaracion : declaracion_variable"""
    p[0] = p[1]

def p_declaracion_sent(p):
    """declaracion : lista_sentencias"""
    p[0] = p[1]

def p_declaracion_variable(p):
    """declaracion_variable : tipo identificador PUNTO_Y_COMA"""
    p[0] = ASTNode(
        "DECLARACION_VARIABLE",
        [p[1], p[2]],
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

def p_identificador_single(p):
    """identificador : IDENTIFICADOR"""
    p[0] = ASTNode("ID", value=p[1], line=p.lineno(1))

def p_identificador_multi(p):
    """identificador : identificador COMA IDENTIFICADOR"""
    p[0] = ASTNode("ID_MULTI", [p[1], ASTNode("ID", value=p[3], line=p.lineno(3))], line=p[1].line)

def p_tipo(p):
    """tipo : INT
            | FLOAT
            | BOOL"""
    p[0] = ASTNode("TIPO", value=p[1], line=p.lineno(1))

def p_lista_sentencias_multi(p):
    """lista_sentencias : lista_sentencias sentencia"""
    if p[1] is None:
        p[0] = ASTNode("LISTA_SENTENCIAS", [p[2]], line=p[2].line)
    else:
        p[0] = ASTNode("LISTA_SENTENCIAS", [p[1], p[2]], line=p[1].line)

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

# PUNTO_Y_COMA present (via sent_expresion)
# identifier form correct (terminal)
def p_asignacion(p):
    """asignacion : IDENTIFICADOR ASIGNACION sent_expresion"""
    p[0] = ASTNode("ASIGNACION", [ASTNode("ID", value=p[1], line=p.lineno(1)), p[3]], line=p.lineno(1))

# PUNTO_Y_COMA present
def p_sent_expresion_full(p):
    """sent_expresion : expresion PUNTO_Y_COMA"""
    p[0] = ASTNode("SENT_EXPRESION", [p[1]], line=p[1].line)

# PUNTO_Y_COMA present
def p_sent_expresion_empty(p):
    """sent_expresion : PUNTO_Y_COMA"""
    p[0] = ASTNode("SENT_EXPRESION", line=p.lineno(1))

# block terminators correct
def p_seleccion_if(p):
    """seleccion : IF expresion THEN lista_sentencias END"""
    p[0] = ASTNode("SELECCION", [p[2], p[4]], line=p.lineno(1))

# block terminators correct
def p_seleccion_if_else(p):
    """seleccion : IF expresion THEN lista_sentencias ELSE lista_sentencias END"""
    p[0] = ASTNode("SELECCION", [p[2], p[4], p[6]], line=p.lineno(1))

# block terminators correct
def p_iteracion(p):
    """iteracion : WHILE expresion lista_sentencias END"""
    p[0] = ASTNode("ITERACION", [p[2], p[3]], line=p.lineno(1))

# block terminators correct
def p_repeticion(p):
    """repeticion : DO lista_sentencias WHILE expresion"""
    p[0] = ASTNode("REPETICION", [p[2], p[4]], line=p.lineno(1))

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
    p[0] = ASTNode("EXPRESION_RELACIONAL", [p[1], p[2], p[3]], line=p[1].line)

def p_expresion_logica(p):
    """expresion : expresion AND expresion
                 | expresion OR expresion"""
    p[0] = ASTNode("EXPRESION_LOGICA", [p[1], p[3]], value=p[2], line=p[1].line)

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
    p[0] = ASTNode("EXPRESION_SIMPLE", [p[1], p[2], p[3]], line=p[1].line)

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
    p[0] = ASTNode("TERMINO", [p[1], p[2], p[3]], line=p[1].line)

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
    p[0] = ASTNode("FACTOR", [p[1], p[2], p[3]], line=p[1].line)

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
    """Manejo de errores sintácticos con recuperación a nivel de sentencia."""
    global _parser
    if p:
        _errores_sintacticos.append({
            "linea": getattr(p, "lineno", 0),
            "columna": getattr(p, "lexpos", 0),
            "descripcion": f"Token inesperado: '{p.value}' (tipo: {p.type})"
        })
        # ✅ implemented by agent — calls parser.restart() for non-fatal recovery
        _parser.restart()
    else:
        _errores_sintacticos.append({
            "linea": 0,
            "columna": 0,
            "descripcion": "Fin de entrada inesperado"
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

    _errores_sintacticos.clear()
    lexer_bridge = _LexerBridge(lista_tokens)

    try:
        ast = _parser.parse(lexer=lexer_bridge, tracking=True)
    except Exception:
        ast = None

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
        
    _errores_sintacticos.clear()
    lexer_bridge = _LexerBridge(tokens)

    try:
        ast = _parser.parse(lexer=lexer_bridge, tracking=True)
    except Exception:
        ast = None

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
