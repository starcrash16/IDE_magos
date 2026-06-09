# IDE Compiladores

IDE gráfico para un compilador de un lenguaje propio, desarrollado por fases para la materia de Compiladores. Construido con Python + PySide6.

## Instalación

```bash
pip install PySide6
```

## Ejecución

```bash
# Iniciar el IDE
python main.py

# Ejecutar el lexer de forma independiente (útil para pruebas rápidas)
python compilador/lexer.py <archivo.txt>

# Ejecutar el parser de forma independiente
python compilador/parser.py <archivo.txt>
```

---

## Estructura del proyecto

```
IDE_magos/
│
├── main.py                  ← Punto de entrada. Define la clase CompiladorIDE
│                              que hereda de SetupInterfaz y QMainWindow.
│
├── ui_setup.py              ← Mixin SetupInterfaz: construcción de todos los
│                              widgets (menús, editor, pestañas, barra de estado,
│                              panel del árbol sintáctico con vista gráfica + lista).
│
├── funciones_ide.py         ← Funciones de manejo de archivos (nuevo, abrir, guardar)
│                              y ejecución de fases del compilador:
│                                ejecutar_lexico()    → invoca compilador/lexer.py
│                                ejecutar_sintactico() → invoca compilador/parser.py
│                              Se inyectan como métodos de CompiladorIDE en main.py.
│
├── syntax_highlighter.py    ← MiHighlighter (QSyntaxHighlighter): resaltado de
│                              sintaxis en tiempo real en el editor de código.
│
├── arbol_grafico.py         ← ArbolGraficoView (QGraphicsView): vista gráfica del
│                              AST con cajas de colores, conectores en escalera,
│                              zoom (Ctrl+rueda) y pan (arrastrar).
│                              También expone la paleta COLORES_NODO y color_para().
│
└── compilador/
    ├── lexer.py             ← Analizador léxico autónomo. Lee un archivo fuente y
    │                          escribe JSON en stdout con la forma:
    │                            { "tokens": [...], "errores": [...] }
    │                          Cada token: { linea, columna, tipo, lexema }
    │
    └── parser.py            ← Analizador sintáctico autónomo (PLY). Lee un archivo
                               fuente, invoca el lexer internamente y escribe JSON:
                                 { "ast": {...}, "tokens": [...],
                                   "errores_lexicos": [...],
                                   "errores_sintacticos": [...] }
                               El AST es un árbol de nodos { type, value, line, children }.
```

### Patrón de diseño

La comunicación entre el IDE y cada fase del compilador se hace por **subprocess + JSON stdout**: el IDE lanza `lexer.py` o `parser.py` como proceso hijo y parsea su salida. Cada nueva fase (semántica, código intermedio, etc.) debe seguir el mismo contrato: un script en `compilador/` que lea un archivo y escriba JSON a stdout.

---

## Estado de las fases

| Fase | Estado |
|---|---|
| UI base + manejo de archivos | ✅ Completo |
| Análisis léxico (`lexer.py`) | ✅ Completo |
| Análisis sintáctico + AST (`parser.py`) | ✅ Completo |
| Análisis semántico | Pendiente |
| Generación de código intermedio | Pendiente |
| Ejecución | Pendiente |

---

## Palabras reservadas del lenguaje

```
if   else   end   do   while   for   switch   case
int  float  main  cin  cout    return
```

## Tipos de token producidos por el léxico

| Tipo | Ejemplos |
|---|---|
| `PALABRA_RESERVADA` | `if`, `while`, `int`, `main` |
| `IDENTIFICADOR` | `x`, `suma`, `miVar` |
| `NUMERO_ENTERO` | `42`, `0`, `100` |
| `NUMERO_REAL` | `3.14`, `0.5` |
| `CADENA` | `"hola mundo"` |
| `CARACTER` | `'a'` |
| `OP_ARITMETICO` | `+` `-` `*` `/` `%` `^` `++` `--` |
| `OP_RELACIONAL` | `<` `<=` `>` `>=` `==` `!=` |
| `OP_LOGICO` | `&&` `\|\|` `!` |
| `ASIGNACION` | `=` |
| `PARENTESIS_IZQ` / `PARENTESIS_DER` | `(` `)` |
| `LLAVE_IZQ` / `LLAVE_DER` | `{` `}` |
| `COMA` | `,` |
| `PUNTO_Y_COMA` | `;` |
| `DOS_PUNTOS` | `:` |
| `INSERCION` | `<<` |
| `EXTRACCION` | `>>` |

---

## Gramática del lenguaje (BNF)

```
programa
    → main { lista_declaracion }

lista_declaracion
    → lista_declaracion declaracion
    | declaracion

declaracion
    → declaracion_variable
    | lista_sentencias

declaracion_variable
    → tipo identificador ;
    | tipo id = expresion ;

identificador
    → id
    | identificador , id

tipo
    → int | float | bool

lista_sentencias
    → lista_sentencias sentencia
    | ε

sentencia
    → seleccion
    | iteracion
    | repeticion
    | sent_in
    | sent_out
    | asignacion

asignacion
    → id = sent_expresion

sent_expresion
    → expresion ;
    | ;

seleccion
    → if expresion then lista_sentencias end
    | if expresion then lista_sentencias else lista_sentencias end

iteracion
    → while expresion lista_sentencias end

repeticion
    → do lista_sentencias while expresion

sent_in
    → cin >> id ;

sent_out
    → cout << salida ;

salida
    → cadena
    | expresion
    | cadena << expresion
    | expresion << cadena

expresion
    → expresion_simple
    | expresion_simple rel_op expresion_simple
    | expresion && expresion
    | expresion || expresion

rel_op
    → < | <= | > | >= | == | !=

expresion_simple
    → expresion_simple suma_op termino
    | termino

suma_op
    → + | - | ++ | --

termino
    → termino mult_op factor
    | factor

mult_op
    → * | / | %

factor
    → factor pot_op componente
    | componente

pot_op
    → ^

componente
    → ( expresion )
    | numero
    | id
    | bool
    | op_logico componente

op_logico
    → && | || | !

cadena
    → CADENA

numero
    → NUMERO_ENTERO | NUMERO_REAL
```
