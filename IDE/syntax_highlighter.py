"""
syntax_highlighter.py — Resaltado de Sintaxis en Tiempo Real
Materia: Compiladores 1

Implementa un QSyntaxHighlighter que colorea el código en el CodeEditor
usando la paleta de VS Code Dark+.

Categorías y colores:
  - Palabras reservadas : #569cd6 (Azul)
  - Números             : #b5cea8 (Verde claro)
  - Comentarios         : #6a9955 (Verde)
  - Op. aritméticos     : #d7ba7d (Amarillo)
  - Op. relac./lógicos  : #ce9178 (Naranja)
  - Cadenas/caracteres  : #ce9178 (Naranja rojizo)
  - Identificadores     : #d4d4d4 (Blanco — color por defecto del editor)
"""

import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


# ══════════════════════════════════════════════════════════════════════════════
# Palabras reservadas del lenguaje
# ══════════════════════════════════════════════════════════════════════════════

PALABRAS_RESERVADAS = [
    "if", "else", "end", "do", "while", "switch", "case",
    "int", "float", "main", "cin", "cout","for","return"
]


class MiHighlighter(QSyntaxHighlighter):
    """
    Resaltador de sintaxis para el lenguaje estilo C/C++ del compilador.
    Se conecta al QDocument del CodeEditor.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Formatos de color ─────────────────────────────────────────────

        # Color 4: Palabras reservadas — Azul (#569cd6)
        self.fmt_reservada = QTextCharFormat()
        self.fmt_reservada.setForeground(QColor("#569cd6"))
        self.fmt_reservada.setFontWeight(QFont.Bold)

        # Color 1: Números — Verde claro (#b5cea8)
        self.fmt_numero = QTextCharFormat()
        self.fmt_numero.setForeground(QColor("#b5cea8"))

        # Color 3: Comentarios — Verde (#6a9955)
        self.fmt_comentario = QTextCharFormat()
        self.fmt_comentario.setForeground(QColor("#6a9955"))
        self.fmt_comentario.setFontItalic(True)

        # Color 5: Op. aritméticos — Amarillo (#d7ba7d)
        self.fmt_aritmetico = QTextCharFormat()
        self.fmt_aritmetico.setForeground(QColor("#d7ba7d"))

        # Color 6: Op. relacionales y lógicos — Naranja (#ce9178)
        self.fmt_relacional_logico = QTextCharFormat()
        self.fmt_relacional_logico.setForeground(QColor("#ce9178"))

        # Cadenas y caracteres — Naranja rojizo (#ce9178)
        self.fmt_cadena = QTextCharFormat()
        self.fmt_cadena.setForeground(QColor("#ce9178"))

        # ── Reglas de resaltado (patrón, formato) ─────────────────────────
        # Se aplican en orden: las últimas reglas tienen prioridad visual.
        self._reglas = []

        # Números reales y enteros
        self._reglas.append((re.compile(r"\b\d+\.\d+\b"), self.fmt_numero))
        self._reglas.append((re.compile(r"\b\d+\b"), self.fmt_numero))

        # Palabras reservadas (como palabras completas con \b)
        patron_reservadas = r"\b(" + "|".join(PALABRAS_RESERVADAS) + r")\b"
        self._reglas.append((re.compile(patron_reservadas), self.fmt_reservada))

        # Operadores aritméticos (los de 2 caracteres primero)
        self._reglas.append((re.compile(r"\+\+|--|[+\-*/%^]"), self.fmt_aritmetico))

        # Operadores relacionales y lógicos
        self._reglas.append((re.compile(r"<=|>=|!=|==|<|>|&&|\|\||!"), self.fmt_relacional_logico))

        # Cadenas entre comillas dobles
        self._reglas.append((re.compile(r'"[^"]*"'), self.fmt_cadena))

        # Caracteres entre comillas simples
        self._reglas.append((re.compile(r"'[^']*'"), self.fmt_cadena))

        # Comentarios de línea (// ...) — aplicar al final para que tenga prioridad
        self._reglas.append((re.compile(r"//[^\n]*"), self.fmt_comentario))

        # ── Comentarios multilínea (/* ... */) ────────────────────────────
        # Requieren tratamiento especial porque pueden abarcar múltiples bloques.
        self._comentario_inicio = re.compile(r"/\*")
        self._comentario_fin = re.compile(r"\*/")

    def highlightBlock(self, texto: str):
        """
        Método llamado por Qt cada vez que un bloque (línea) necesita
        ser re-resaltado. Aplica las reglas de una sola línea y luego
        maneja los comentarios multilínea.
        """
        # ── 1. Aplicar reglas de una sola línea ──────────────────────────
        for patron, formato in self._reglas:
            for match in patron.finditer(texto):
                inicio = match.start()
                longitud = match.end() - match.start()
                self.setFormat(inicio, longitud, formato)

        # ── 2. Manejar comentarios multilínea (/* ... */) ────────────────
        # Qt usa "estados de bloque" para saber si estamos dentro de un
        # comentario que empezó en una línea anterior.
        # Estado  0 = Normal (fuera de comentario multilínea)
        # Estado  1 = Dentro de un comentario multilínea

        self.setCurrentBlockState(0)

        # Determinar desde dónde empezar a buscar en esta línea
        inicio_busqueda = 0

        if self.previousBlockState() != 1:
            # No estamos dentro de un comentario multilínea previo.
            # Buscar si hay un /* en esta línea.
            match_inicio = self._comentario_inicio.search(texto)
            if match_inicio:
                inicio_busqueda = match_inicio.start()
            else:
                return  # No hay comentario multilínea en esta línea
        else:
            # Estamos dentro de un comentario multilínea previo.
            inicio_busqueda = 0

        # Procesar comentarios multilínea
        while inicio_busqueda >= 0:
            match_fin = self._comentario_fin.search(texto, inicio_busqueda)

            if match_fin is None:
                # No se encontró cierre */ en esta línea → todo lo que queda es comentario
                self.setCurrentBlockState(1)
                longitud = len(texto) - inicio_busqueda
            else:
                # Se encontró cierre */ → colorear hasta el cierre
                longitud = match_fin.end() - inicio_busqueda

            self.setFormat(inicio_busqueda, longitud, self.fmt_comentario)

            if match_fin is None:
                break  # Continúa en la siguiente línea

            # Buscar si hay otro /* después del cierre
            match_siguiente = self._comentario_inicio.search(texto, match_fin.end())
            if match_siguiente:
                inicio_busqueda = match_siguiente.start()
            else:
                break
