"""
arbol_grafico.py
Vista gráfica del Árbol Sintáctico Abstracto (AST) para CompiladorIDE.

Dibuja el AST como un árbol de cajas coloreadas unidas por conectores en
escalera, al estilo del CanvasArbol de la versión Tkinter de referencia, pero
implementado sobre QGraphicsView/QGraphicsScene (PySide6).

Expone:
    COLORES_NODO            -> dict {tipo: (bg, borde/texto)} compartido con el árbol-lista
    color_para(tipo)        -> (bg, fg) con fallback
    ArbolGraficoView        -> QGraphicsView con dibujar()/zoom
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRectF


# ──────────────────────────────────────────────────────────────────────────────
# Paleta — color de ACENTO por tipo de nodo.
# Reutiliza los mismos colores que la tabla de Tokens del IDE (tema VS Code)
# para que el árbol combine visualmente con el resto de la interfaz.
#   azul     #4fc1ff  estructura / relacional
#   teal     #4ec9b0  tipos / cin·cout
#   verde    #b5cea8  números
#   amarillo #d7ba7d  operadores aritméticos
#   morado   #c586c0  control de flujo / lógicos
#   naranja  #ce9178  cadenas
#   dorado   #ffd700  asignación
#   var      #9cdcfe  identificadores
#   gris     #858585  nodos neutros
# ──────────────────────────────────────────────────────────────────────────────
COLOR_FONDO_IDE = "#1e1e1e"   # fondo base del IDE (editor / paneles)

COLORES_NODO = {
    # Estructura del programa
    "PROGRAMA":             "#4fc1ff",
    "LISTA_DECLARACION":    "#4fc1ff",
    "LISTA_SENTENCIAS":     "#4fc1ff",
    "BLOQUE":               "#4fc1ff",   # AST: equivale a LISTA_SENTENCIAS
    "VACIO":                "#858585",   # AST: sentencia/expresión vacía

    # Declaraciones / tipos
    "DECLARACION_VARIABLE": "#4ec9b0",
    "TIPO":                 "#4ec9b0",

    # Identificadores
    "ID":                   "#9cdcfe",
    "ID_MULTI":             "#9cdcfe",
    "COMPONENTE_ID":        "#9cdcfe",

    # Control de flujo
    "SELECCION":            "#c586c0",
    "ITERACION":            "#c586c0",
    "REPETICION":           "#c586c0",

    # Entrada / salida
    "SENT_IN":              "#4ec9b0",
    "SENT_OUT":             "#4ec9b0",
    "SALIDA_CADENA":        "#ce9178",
    "SALIDA_EXPRESION":     "#ce9178",
    "SALIDA_MIXTA":         "#ce9178",

    # Asignación
    "ASIGNACION":           "#ffd700",
    "SENT_EXPRESION":       "#858585",

    # Expresiones / operadores
    "EXPRESION_RELACIONAL": "#4fc1ff",
    "EXPRESION_LOGICA":     "#c586c0",
    "EXPRESION_SIMPLE":     "#d7ba7d",
    "TERMINO":              "#d7ba7d",
    "FACTOR":               "#d7ba7d",
    "COMPONENTE_UNARIO":    "#c586c0",
    "REL_OP":               "#4fc1ff",
    "SUMA_OP":              "#d7ba7d",
    "MULT_OP":              "#d7ba7d",
    "POT_OP":               "#d7ba7d",
    "OP_LOGICO":            "#c586c0",

    # Literales
    "NUMERO":               "#b5cea8",
    "COMPONENTE_BOOL":      "#569cd6",

    # Errores sintácticos (nodo de recuperación)  → rojo
    "ERROR_SINTACTICO":     "#ff6b6b",
}
_ACENTO_DEFAULT = "#d4d4d4"


def _mezclar(hex_a, hex_b, t):
    """Mezcla linealmente dos colores hex (t=0 → a, t=1 → b)."""
    a = QColor(hex_a)
    b = QColor(hex_b)
    r = round(a.red()   * (1 - t) + b.red()   * t)
    g = round(a.green() * (1 - t) + b.green() * t)
    bl = round(a.blue() * (1 - t) + b.blue()  * t)
    return QColor(r, g, bl).name()


def color_para(tipo):
    """
    Devuelve (bg, fg) para un tipo de nodo.
    fg = color de acento; bg = fondo del IDE teñido sutilmente con ese acento,
    para que cada caja conserve identidad sin romper el tema oscuro.
    """
    fg = COLORES_NODO.get(tipo, _ACENTO_DEFAULT)
    bg = _mezclar(COLOR_FONDO_IDE, fg, 0.16)
    return bg, fg


class ArbolGraficoView(QGraphicsView):
    """Dibuja un AST (dict) como árbol gráfico de cajas con zoom y pan."""

    # Dimensiones base de la cuadrícula del árbol
    NODE_W = 150   # ancho de cada caja
    NODE_H = 48    # alto de cada caja
    HGAP   = 26    # separación horizontal entre subárboles hermanos
    VGAP   = 46    # separación vertical entre niveles
    PAD    = 40    # margen exterior de la escena

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)   # arrastrar = pan
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        self.setStyleSheet("border: 1px solid #3e3e3e;")

        self._scale = 1.0
        self._pos = {}            # id(nodo) -> (cx, cy)
        self._highlight_item = None

    # ── API pública ────────────────────────────────────────────────────────
    def dibujar(self, ast_dict):
        """Reconstruye la escena a partir de un nodo AST (dict) o None."""
        self._scene.clear()
        self._pos.clear()
        self._highlight_item = None

        if not ast_dict:
            aviso = self._scene.addText(
                "⚠  Sin árbol sintáctico (errores críticos en el código)",
                QFont("Consolas", 11),
            )
            aviso.setDefaultTextColor(QColor("#ff6b6b"))
            return

        self._medir(ast_dict)
        self._colocar(ast_dict, self.PAD, 0)
        self._dibujar_conectores(ast_dict)
        self._dibujar_cajas(ast_dict)

        rect = self._scene.itemsBoundingRect()
        self._scene.setSceneRect(rect.adjusted(-self.PAD, -self.PAD,
                                               self.PAD, self.PAD))

    def zoom_in(self):
        self._aplicar_zoom(1.2)

    def zoom_out(self):
        self._aplicar_zoom(1 / 1.2)

    def zoom_reset(self):
        self.resetTransform()
        self._scale = 1.0

    def ajustar(self):
        """Encrusta todo el árbol dentro de la vista."""
        if self._scene.itemsBoundingRect().isValid():
            self.fitInView(self._scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self._scale = self.transform().m11()

    def highlight_nodo(self, node):
        """Centra la vista en el nodo y dibuja un borde de selección sobre él."""
        if node is None:
            return
        nid = id(node)
        if nid not in self._pos:
            return

        # Eliminar highlight anterior
        if self._highlight_item is not None:
            self._scene.removeItem(self._highlight_item)
            self._highlight_item = None

        cx, cy = self._pos[nid]

        # Borde brillante alrededor del nodo
        margen = 6
        x1 = cx - self.NODE_W / 2 - margen
        y1 = cy - self.NODE_H / 2 - margen
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(x1, y1, self.NODE_W + margen * 2, self.NODE_H + margen * 2),
            11, 11
        )
        pen = QPen(QColor("#ffffff"), 2.5, Qt.DashLine)
        pen.setDashPattern([4, 3])
        self._highlight_item = self._scene.addPath(path, pen, QBrush(Qt.NoBrush))

        # Centrar la vista en el nodo seleccionado
        self.centerOn(cx, cy)

    # ── Zoom con Ctrl + rueda ──────────────────────────────────────────────
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._aplicar_zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
            event.accept()
        else:
            super().wheelEvent(event)

    def _aplicar_zoom(self, factor):
        nuevo = self._scale * factor
        if nuevo < 0.2 or nuevo > 4.0:
            return
        self._scale = nuevo
        self.scale(factor, factor)

    # ── Cálculo de layout ──────────────────────────────────────────────────
    def _hijos(self, node):
        return [h for h in node.get("children", []) if h]

    def _medir(self, node):
        """Ancho del subárbol en píxeles (post-orden)."""
        hijos = self._hijos(node)
        if not hijos:
            ancho = self.NODE_W
        else:
            ancho = sum(self._medir(h) for h in hijos) + self.HGAP * (len(hijos) - 1)
            ancho = max(self.NODE_W, ancho)
        node["_w"] = ancho
        return ancho

    def _colocar(self, node, x_left, depth):
        """Asigna el centro (cx, cy) de cada nodo (pre-orden)."""
        hijos = self._hijos(node)
        cy = depth * (self.NODE_H + self.VGAP) + self.NODE_H / 2

        if not hijos:
            cx = x_left + self.NODE_W / 2
        else:
            cursor = x_left
            centros = []
            for h in hijos:
                self._colocar(h, cursor, depth + 1)
                centros.append(self._pos[id(h)][0])
                cursor += h["_w"] + self.HGAP
            cx = (centros[0] + centros[-1]) / 2

        self._pos[id(node)] = (cx, cy)

    # ── Dibujo ─────────────────────────────────────────────────────────────
    def _dibujar_conectores(self, node):
        cx, cy = self._pos[id(node)]
        pen = QPen(QColor("#555555"), 1.4)
        for h in self._hijos(node):
            hx, hy = self._pos[id(h)]
            my = (cy + self.NODE_H / 2 + hy - self.NODE_H / 2) / 2
            path = QPainterPath()
            path.moveTo(cx, cy + self.NODE_H / 2)
            path.lineTo(cx, my)
            path.lineTo(hx, my)
            path.lineTo(hx, hy - self.NODE_H / 2)
            self._scene.addPath(path, pen)
            self._dibujar_conectores(h)

    def _dibujar_cajas(self, node):
        cx, cy = self._pos[id(node)]
        bg, fg = color_para(node.get("type", ""))

        x1 = cx - self.NODE_W / 2
        y1 = cy - self.NODE_H / 2

        # Sombra sutil
        sombra = QPainterPath()
        sombra.addRoundedRect(QRectF(x1 + 2, y1 + 3, self.NODE_W, self.NODE_H), 8, 8)
        self._scene.addPath(sombra, QPen(Qt.NoPen), QBrush(QColor("#141414")))

        # Caja
        caja = QPainterPath()
        caja.addRoundedRect(QRectF(x1, y1, self.NODE_W, self.NODE_H), 8, 8)
        self._scene.addPath(caja, QPen(QColor(fg), 1.6), QBrush(QColor(bg)))

        # Texto: tipo (negrita) + sub-etiqueta (valor o línea)
        tipo = str(node.get("type", ""))
        valor = node.get("value")
        linea = node.get("line")

        sub = ""
        if valor is not None:
            vs = str(valor)
            sub = (vs[:14] + "…") if len(vs) > 15 else vs
        elif linea:
            sub = f"L{linea}"

        if sub:
            self._texto(tipo, cx, cy - 8, fg, 9, bold=True)
            self._texto(sub, cx, cy + 9, fg, 8, bold=False)
        else:
            self._texto(tipo, cx, cy, fg, 9, bold=True)

        for h in self._hijos(node):
            self._dibujar_cajas(h)

    def _texto(self, texto, cx, cy, color, tam, bold):
        font = QFont("Consolas", tam)
        font.setBold(bold)
        item = self._scene.addSimpleText(texto, font)
        item.setBrush(QBrush(QColor(color)))
        r = item.boundingRect()
        item.setPos(cx - r.width() / 2, cy - r.height() / 2)
