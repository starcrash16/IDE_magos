# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the application

```bash
# Activate the virtual environment first
source venv/bin/activate

# Launch the IDE
python main.py

# Run the lexer standalone (useful for quick testing)
python compilador/lexer.py prueba.txt
```

**Dependency:** `pip install PySide6` (only external dependency).

## Architecture

This is a graphical compiler IDE built with Python + PySide6, developed phase-by-phase for a Compilers course. The class composition pattern is intentional: functions are defined at module level and injected as methods onto `CompiladorIDE` at import time.

```
main.py                  ← Entry point; defines CompiladorIDE class
ui_setup.py              ← SetupInterfaz mixin: all widget construction
funciones_ide.py         ← File I/O methods + ejecutar_lexico() / ejecutar_sintactico() / ejecutar_semantico() (injected into the class)
syntax_highlighter.py    ← MiHighlighter (QSyntaxHighlighter): real-time coloring
arbol_grafico.py         ← ArbolGraficoView: graphical tree (dibujar(ast, con_atributos=True) shows semantic attributes)
compilador/lexer.py      ← Standalone lexer; communicates with IDE via subprocess + JSON stdout
compilador/parser.py     ← Standalone parser (PLY); calls lexer internally, outputs AST + errors as JSON
compilador/semantico.py  ← Standalone semantic analyzer; calls parser, outputs annotated AST + symbol table + trace + errors as JSON
```

### Key design decisions

**IPC via subprocess:** `ejecutar_lexico()` and `ejecutar_sintactico()` in `funciones_ide.py` invoke `compilador/lexer.py` and `compilador/parser.py` respectively as child processes and parse their JSON stdout. Each future compiler phase (semantic, etc.) should follow the same pattern: a standalone script in `compilador/` that reads a file and writes JSON to stdout.

**Mixin injection pattern:** `SetupInterfaz` (in `ui_setup.py`) is a plain class with no Qt inheritance — it relies on `self` being a `QMainWindow`. File functions in `funciones_ide.py` are module-level functions that also use `self` and are assigned directly to `CompiladorIDE` as class attributes in `main.py`.

**Lexer contract:** `compilador/lexer.py` exposes one public function `analizar(codigo_fuente: str) -> dict` and a CLI entry point. It always returns `{"tokens": [...], "errores": [...]}`. Token shape: `{"linea", "columna", "tipo", "lexema"}`. Error shape: `{"linea", "columna", "descripcion"}`.

**AST shape:** every node is `{"type", "value", "line", "column", "children"}` (column is 1-based, from the token). `OPERACION` nodes take line/column from the operator.

**Semantic contract:** `compilador/semantico.py` exposes `analizar(codigo_fuente) -> dict` returning `{"ast", "ast_anotado", "tabla_simbolos", "traza", "errores_lexicos", "errores_sintacticos", "errores_semanticos"}`. `ast_anotado` is a deep copy of `ast` (same shape) where nodes carry an `"atributos"` dict: `dtype` (inherited), `tipo` / `valor` (synthesized; `valor` only when computable at compile time), `dir`, `conversion` (e.g. `"int→float"`), `error`. Its JSON output uses `ensure_ascii=True` so the subprocess pipe is encoding-independent; `--reporte` prints a UTF-8 text report instead.

**Type rules:** single global scope; `int`+`float` → `float` (int operand gets `conversion`); `/` between ints is integer division; `%` int only; relational → `bool`; `&& || !` bool only; assigning `float` to `int` is an error ("Conversión no válida"), `int` to `float` is an implicit conversion; `if/while/do/for` conditions must be `bool`. Constant values propagate through variables, but are invalidated for variables modified inside loops / if-branches. `true`/`false` are not keywords, so they are reported as undeclared identifiers.

### Token types produced by the lexer

`PALABRA_RESERVADA`, `IDENTIFICADOR`, `NUMERO_ENTERO`, `NUMERO_REAL`, `CADENA`, `CARACTER`, `OP_ARITMETICO`, `OP_RELACIONAL`, `OP_LOGICO`, `ASIGNACION`, `PARENTESIS_IZQ`, `PARENTESIS_DER`, `LLAVE_IZQ`, `LLAVE_DER`, `COMA`, `PUNTO_Y_COMA`, `DOS_PUNTOS`, `INSERCION`, `EXTRACCION`

### Target language keywords

`if else end do while switch case int float main cin cout for return`

## Current phase status

| Phase | Status |
|-------|--------|
| UI base + file management | Complete |
| Lexical analysis (`compilador/lexer.py`) | Complete |
| Syntax analysis (`compilador/parser.py`) | ✅ Complete |
| Semantic analysis (`compilador/semantico.py`) | ✅ Complete |
| Intermediate code generation | Placeholder |
| Execution | Placeholder |

The result tabs (`Cód. Intermedio`, `Ejecución`) and their menu actions are already wired into the UI in `ui_setup.py`. New phases only need: a script in `compilador/`, a function in `funciones_ide.py`, and connecting that function to the corresponding `QAction` in `ui_setup.py`. `_guardar_antes_de_compilar()` and `_correr_script_compilador()` in `funciones_ide.py` handle saving + running a `compilador/` script.

The `Semántica` tab shows AST original | AST anotado (selection is synced by tree position) | recorrido semántico; the `Símbolos` tab shows the symbol table. `prueba_semantica.txt` exercises every semantic rule and error.

```bash
# Semantic report (annotated tree, symbol table, errors, trace) from the terminal
python compilador/semantico.py prueba_semantica.txt --reporte
```
