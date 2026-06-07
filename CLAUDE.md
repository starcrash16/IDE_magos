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
funciones_ide.py         ← File I/O methods + ejecutar_lexico() (injected into the class)
syntax_highlighter.py    ← MiHighlighter (QSyntaxHighlighter): real-time coloring
compilador/lexer.py      ← Standalone lexer; communicates with IDE via subprocess + JSON stdout
```

### Key design decisions

**IPC via subprocess:** `ejecutar_lexico()` in `funciones_ide.py` invokes `compilador/lexer.py` as a child process and parses its JSON stdout. Each future compiler phase (parser, semantic, etc.) should follow the same pattern: a standalone script in `compilador/` that reads a file and writes JSON to stdout.

**Mixin injection pattern:** `SetupInterfaz` (in `ui_setup.py`) is a plain class with no Qt inheritance — it relies on `self` being a `QMainWindow`. File functions in `funciones_ide.py` are module-level functions that also use `self` and are assigned directly to `CompiladorIDE` as class attributes in `main.py`.

**Lexer contract:** `compilador/lexer.py` exposes one public function `analizar(codigo_fuente: str) -> dict` and a CLI entry point. It always returns `{"tokens": [...], "errores": [...]}`. Token shape: `{"linea", "columna", "tipo", "lexema"}`. Error shape: `{"linea", "columna", "descripcion"}`.

### Token types produced by the lexer

`PALABRA_RESERVADA`, `IDENTIFICADOR`, `NUMERO_ENTERO`, `NUMERO_REAL`, `CADENA`, `CARACTER`, `OP_ARITMETICO`, `OP_RELACIONAL`, `OP_LOGICO`, `ASIGNACION`, `PARENTESIS_IZQ`, `PARENTESIS_DER`, `LLAVE_IZQ`, `LLAVE_DER`, `COMA`, `PUNTO_Y_COMA`, `DOS_PUNTOS`, `INSERCION`, `EXTRACCION`

### Target language keywords

`if else end do while switch case int float main cin cout for return`

## Current phase status

| Phase | Status |
|-------|--------|
| UI base + file management | Complete |
| Lexical analysis (`compilador/lexer.py`) | Complete |
| Syntax analysis | Placeholder (menu action exists, no implementation) |
| Semantic analysis | Placeholder |
| Intermediate code generation | Placeholder |
| Execution | Placeholder |

The result tabs (`Árbol Sintáctico`, `Semántica`, `Cód. Intermedio`, `Ejecución`) and their menu actions are already wired into the UI in `ui_setup.py`. New phases only need: a script in `compilador/`, a function in `funciones_ide.py`, and connecting that function to the corresponding `QAction` in `ui_setup.py`.
