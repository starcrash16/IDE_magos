"""
Contiene toda la lógica de creación y configuración de widgets.
Se usa como clase base en main.py:
    class CompiladorIDE(SetupInterfaz, QMainWindow)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QToolBar,
    QStatusBar, QStyle, QLabel,
    QPlainTextEdit, QTextEdit,
    QTreeView
)

from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtCore import QDir
from PySide6.QtGui import QAction, QPainter, QTextFormat, QFontDatabase
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import QTreeView
from PySide6.QtWidgets import QSplitter
from PySide6.QtGui import QColor

# Resaltador de sintaxis para el editor de código
from syntax_highlighter import MiHighlighter

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._lineNumberArea = LineNumberArea(self)

        # señales para refrescar gutter
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        # evita saltos en el scroll horizontal
        
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        # 3px margen + ancho por dígito
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self._lineNumberArea.scroll(0, dy)
        else:
            self._lineNumberArea.update(0, rect.y(), self._lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self._lineNumberArea)
        painter.fillRect(event.rect(), self.palette().window())

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(self.palette().text().color())
                painter.drawText(
                    0, top, self._lineNumberArea.width() - 4, self.fontMetrics().height(),
                    Qt.AlignRight, number
                )

            block = block.next()
            blockNumber += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(255, 255, 255, 40))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)

            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)

        self.setExtraSelections(extraSelections)

    def cursorLineColumn(self):
        c = self.textCursor()
        line = c.blockNumber() + 1
        col = c.positionInBlock() + 1
        return line, col

class SetupInterfaz:
    """Clase que agrupa todos los métodos de construcción de la interfaz."""

    # ─── Inicialización principal ─────────────────────────────────────────────

    """
    Metodos utilizados:
    - QWidget(): Crea un contenedor genérico para agrupar otros elementos de la UI.
    - QVBoxLayout(parent): Crea un organizador o un grid que apila los elementos de forma vertical.
    - setCentralWidget(widget): Establece el widget que ocupará el área principal de la ventana.
    - addWidget(widget, stretch): Añade un elemento al diseño vertical = 'stretch' e indica la prioridad de espacio.
    - QTabWidget(): Proporciona una barra de pestañas para cambiar entre diferentes paneles.
    - QStatusBar(): Crea la barra en la parte inferior de la ventana para mostrar información.
    - setStatusBar(bar): Asigna oficialmente la barra de estado a la ventana principal (QMainWindow).
    - connect(metodo): Conecta una señal (evento) con una ranura (función a ejecutar).
    """

    def crear_barra_actividades(self):
        self.barra_actividades = QFrame()
        self.barra_actividades.setFixedWidth(50)
        self.barra_actividades.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
            }
            QPushButton {
                border: none;
                padding: 10px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
        """)

        layout = QVBoxLayout(self.barra_actividades)
        layout.setAlignment(Qt.AlignTop)

        # Botones estilo VS Code
        self.btn_explorador = QPushButton("📁")
        self.btn_buscar = QPushButton("🔍")
        self.btn_compilar = QPushButton("⚙")
        self.btn_ejecutar = QPushButton("▶")

        layout.addWidget(self.btn_explorador)
        layout.addWidget(self.btn_buscar)
        layout.addWidget(self.btn_compilar)
        layout.addWidget(self.btn_ejecutar)
        # ─── Explorer tipo VS Code ─────────────────────────────
    def crear_explorer(self):
        self.explorer_model = QFileSystemModel()
        self.explorer_model.setRootPath(QDir.currentPath())

        self.explorer = QTreeView()
        self.explorer.setModel(self.explorer_model)
        self.explorer.setRootIndex(
            self.explorer_model.index(QDir.currentPath())
        )

        # Mostrar solo la columna del nombre
        self.explorer.hideColumn(1)
        self.explorer.hideColumn(2)
        self.explorer.hideColumn(3)

        # Estilo oscuro tipo VS Code
        self.explorer.setStyleSheet("""
            QTreeView {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
            }
            QTreeView::item:selected {
                background-color: #264f78;
            }
        """)

        # Doble clic abre archivo
        self.explorer.doubleClicked.connect(self.abrir_archivo_desde_explorer)


    def abrir_archivo_desde_explorer(self, index):
        ruta = self.explorer_model.filePath(index)

        if not self.explorer_model.isDir(index):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    contenido = f.read()
                    self.editor.setPlainText(contenido)
            except Exception as e:
                self.barra_estado.showMessage(f"Error al abrir archivo: {e}")

    def inicializar_interfaz(self):


        # 1. Configurar Menús y Barra de Herramientas
        self.crear_menus()
        self.crear_barra_herramientas()

        # ─────────────────────────────────────────────
        # Widget Central Principal
        # ─────────────────────────────────────────────
        widget_central = QWidget()
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(widget_central)

        # ─────────────────────────────────────────────
        # Splitter Horizontal (Explorer | Editor+Tabs)
        # ─────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        layout_principal.addWidget(splitter)

        # ─────────────────────────────────────────────
        # Explorer
        # ─────────────────────────────────────────────
        self.crear_explorer()
        splitter.addWidget(self.explorer)

        # ─────────────────────────────────────────────
        # Contenedor Derecho
        # ─────────────────────────────────────────────
        contenedor_derecho = QWidget()
        layout_editor = QVBoxLayout(contenedor_derecho)
        layout_editor.setContentsMargins(0, 0, 0, 0)

        splitter.addWidget(contenedor_derecho)

        # Proporciones iniciales (Explorer pequeño)
        splitter.setSizes([250, 900])

        # ─────────────────────────────────────────────
        # Editor
        # ─────────────────────────────────────────────
        self.editor = CodeEditor()

        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.editor.setFont(fixed_font)

        # Aplicar tema oscuro al editor para que el resaltado de sintaxis sea visible
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }
        """)

        # Instanciar el resaltador de sintaxis sobre el documento del editor
        self.highlighter = MiHighlighter(self.editor.document())

        self.editor.cursorPositionChanged.connect(self.actualizar_posicion_cursor)

        layout_editor.addWidget(self.editor, stretch=6)

        # ─────────────────────────────────────────────
        # Tabs
        # ─────────────────────────────────────────────
        self.tabs_resultados = QTabWidget()
        self.configurar_paneles_resultados()

        layout_editor.addWidget(self.tabs_resultados, stretch=4)

        # ─────────────────────────────────────────────
        # Barra de Estado
        # ─────────────────────────────────────────────
        self.barra_estado = QStatusBar()
        self.setStatusBar(self.barra_estado)

        self.lbl_pos = QLabel("Línea: 1 | Columna: 1")
        self.barra_estado.addPermanentWidget(self.lbl_pos)

        self.actualizar_posicion_cursor()

        # Widgets permanentes (no se pisan con showMessage)
        self.lbl_pos = QLabel("Línea: 1 | Columna: 1")
        self.barra_estado.addPermanentWidget(self.lbl_pos)

        self.actualizar_posicion_cursor()

    # ─── Menús ────────────────────────────────────────────────────────────────

    def crear_menus(self):
        """Crea la barra de menús superior y configura sus acciones."""
        barra_menus = self.menuBar()

        # ── Menú Archivo ─────────────────────────────────────────────────────────
        menu_archivo = barra_menus.addMenu("Archivo")

        self.act_nuevo = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Nuevo", self)
        self.act_nuevo.setShortcut("Ctrl+N")
        self.act_nuevo.setStatusTip("Crear un archivo nuevo")
        self.act_nuevo.triggered.connect(self.nuevo_archivo)
        menu_archivo.addAction(self.act_nuevo)

        self.act_abrir = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Abrir", self)
        self.act_abrir.setShortcut("Ctrl+O")
        self.act_abrir.setStatusTip("Abrir un archivo existente")
        self.act_abrir.triggered.connect(self.abrir_archivo)
        menu_archivo.addAction(self.act_abrir)

        self.act_guardar = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Guardar", self)
        self.act_guardar.setShortcut("Ctrl+S")
        self.act_guardar.setStatusTip("Guardar el archivo actual")
        self.act_guardar.triggered.connect(self.guardar_archivo)
        menu_archivo.addAction(self.act_guardar)

        self.act_guardar_como = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Guardar como", self)
        self.act_guardar_como.setShortcut("Ctrl+Shift+S")
        self.act_guardar_como.setStatusTip("Guardar con un nombre nuevo")
        self.act_guardar_como.triggered.connect(self.guardar_como_archivo)
        menu_archivo.addAction(self.act_guardar_como)

        menu_archivo.addSeparator()

        self.act_salir = QAction(self.style().standardIcon(QStyle.SP_DialogCloseButton), "Salir", self)
        self.act_salir.setShortcut("Alt+F4")
        self.act_salir.setStatusTip("Cerrar el IDE")
        self.act_salir.triggered.connect(self.close)
        menu_archivo.addAction(self.act_salir)

        # ── Menú Compilar ────────────────────────────────────────────────────────
        menu_compilar = barra_menus.addMenu("Compilar")

        self.act_lexico = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Ejecutar Léxico", self)
        self.act_sintactico = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Ejecutar Sintáctico", self)
        self.act_semantico = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Ejecutar Semántico", self)
        self.act_intermedio = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "Generar Cód. Intermedio", self)
        self.act_ejecutar = QAction(self.style().standardIcon(QStyle.SP_CommandLink), "Ejecutar", self)

        menu_compilar.addAction(self.act_lexico)
        menu_compilar.addAction(self.act_sintactico)
        menu_compilar.addAction(self.act_semantico)
        menu_compilar.addAction(self.act_intermedio)
        menu_compilar.addSeparator()
        menu_compilar.addAction(self.act_ejecutar)

        # ── Conectar acciones del compilador ──────────────────────────────────
        self.act_lexico.triggered.connect(self.ejecutar_lexico)
        self.act_sintactico.triggered.connect(self.ejecutar_sintactico)
        
    # ─── Barra de Herramientas ────────────────────────────────────────────────

    def crear_barra_herramientas(self):
        toolbar = QToolBar("Acceso Rápido")
        toolbar.setMovable(False)      # se siente más IDE
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        # --- Archivo
        toolbar.addAction(self.act_nuevo)
        toolbar.addAction(self.act_abrir)
        toolbar.addAction(self.act_guardar)
        toolbar.addSeparator()

        # --- Compilar
        toolbar.addAction(self.act_lexico)
        toolbar.addAction(self.act_sintactico)
        toolbar.addAction(self.act_semantico)
        toolbar.addAction(self.act_intermedio)
        toolbar.addSeparator()
        toolbar.addAction(self.act_ejecutar)

    # ─── Paneles de Resultados ────────────────────────────────────────────────
    
    """
    Metodos:
    - QTableWidget(r, c): Crea una estructura de tabla con r filas y c columnas.
    - setHorizontalHeaderLabels([...]): Define los encabezados de cada columna en la tabla.
    - QTextEdit(): Crea un área de edición de texto (utilizada para visualizar salidas).
    - setReadOnly(True): Deshabilita la edición por parte del usuario, convirtiendo el área en solo lectura.
    - addTab(widget, "título"): Agrega el componente visual al panel de pestañas con un nombre específico.

    Logica:
        Se crean componentes especializados para cada tipo de dato (Tablas para tokens/errores y Áreas de texto 
        para árboles/consolas). 
        Se configuran como solo lectura para evitar ediciones accidentales y finalmente 
        se a plian dentro de un contenedor de pestañas **(QTabWidget) *, permitiendo navegar entre las diferentes 
        etapas del proceso de compilación de forma organizada.
    """

    def configurar_paneles_resultados(self):
        # ── Estilo oscuro compartido para todas las tablas ────────────────
        estilo_tabla = """
            QTableWidget {
                background-color: #1e1e1e;
                color: #f5f5f5;
                gridline-color: #555555;
                border: 1px solid #3e3e3e;
                alternate-background-color: #252526;
            }
            QTableWidget::item {
                padding: 4px;
            }git 
            QTableWidget::item:selected {
                background-color: #264f78;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #3e3e3e;
                font-weight: bold;
            }
        """

        # Estilo oscuro compartido para las áreas de texto
        estilo_texto = """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
            }
        """

        # ── Tabla de Tokens ───────────────────────────────────────────────
        self.tabla_tokens = QTableWidget(0, 4)
        self.tabla_tokens.setHorizontalHeaderLabels(["Línea", "Columna", "Token", "Lexema"])
        self.tabla_tokens.setStyleSheet(estilo_tabla)
        self.tabla_tokens.horizontalHeader().setStretchLastSection(True)
        self.tabla_tokens.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_tokens.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_tokens.setAlternatingRowColors(True)

        # ── Tabla de Símbolos ─────────────────────────────────────────────
        self.tabla_simbolos = QTableWidget(0, 4)
        self.tabla_simbolos.setHorizontalHeaderLabels(["ID", "Tipo", "Valor", "Línea"])
        self.tabla_simbolos.setStyleSheet(estilo_tabla)
        self.tabla_simbolos.horizontalHeader().setStretchLastSection(True)
        self.tabla_simbolos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_simbolos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_simbolos.setAlternatingRowColors(True)

        # ── Tabla de Errores ──────────────────────────────────────────────
        self.lista_errores = QTableWidget(0, 4)
        self.lista_errores.setHorizontalHeaderLabels(["Tipo", "Línea", "Columna", "Descripción"])
        self.lista_errores.setStyleSheet(estilo_tabla)
        self.lista_errores.horizontalHeader().setStretchLastSection(True)
        self.lista_errores.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lista_errores.setSelectionBehavior(QTableWidget.SelectRows)
        self.lista_errores.setAlternatingRowColors(True)

        # ── Áreas de Texto ────────────────────────────────────────────────
        # ✅ implemented by agent — QTreeWidget for syntax tree
        from PySide6.QtWidgets import QTreeWidget
        self.arbol_sintactico = QTreeWidget()
        self.arbol_sintactico.setHeaderLabels(["Nodo", "Valor", "Línea"])
        self.arbol_sintactico.setStyleSheet(estilo_tabla)

        self.analisis_semantico = QTextEdit()
        self.analisis_semantico.setReadOnly(True)
        self.analisis_semantico.setStyleSheet(estilo_texto)

        self.codigo_intermedio = QTextEdit()
        self.codigo_intermedio.setReadOnly(True)
        self.codigo_intermedio.setStyleSheet(estilo_texto)

        self.consola_ejecucion = QTextEdit()
        self.consola_ejecucion.setReadOnly(True)
        self.consola_ejecucion.setStyleSheet(estilo_texto)

        # ── Agregar pestañas ──────────────────────────────────────────────
        self.tabs_resultados.addTab(self.tabla_tokens,      "Tokens")
        self.tabs_resultados.addTab(self.arbol_sintactico,  "Árbol Sintáctico")
        self.tabs_resultados.addTab(self.analisis_semantico, "Semántica")
        self.tabs_resultados.addTab(self.codigo_intermedio, "Cód. Intermedio")
        self.tabs_resultados.addTab(self.tabla_simbolos,    "Símbolos")
        self.tabs_resultados.addTab(self.lista_errores,     "Errores")
        self.tabs_resultados.addTab(self.consola_ejecucion, "Ejecución")

    # ─── Barra de Estado ──────────────────────────────────────────────────────

    """
    Metodos:
    - textCursor(): Recupera el objeto cursor que contiene la información de posición del editor.
    - blockNumber(): Devuelve el número de fila (bloque) actual empezando desde 0.
    - columnNumber(): Devuelve la posición del cursor dentro de la fila empezando desde 0.
    - showMessage(texto): Muestra temporalmente un mensaje en la barra de estado.
    
    Logica: 
        Cada vez que el cursor se mueve, se capturan sus coordenadas base 0 y se suma 1 a cada valor.
        Se reinicia (formatea) el texto para mostrarlo constantemente en la parte inferior de la ventana
    """

    def actualizar_posicion_cursor(self):
        # Si usas CodeEditor:
        if hasattr(self.editor, "cursorLineColumn"):
            linea, columna = self.editor.cursorLineColumn()
        else:
            # fallback si algún día vuelves a QTextEdit
            cursor = self.editor.textCursor()
            linea = cursor.blockNumber() + 1
            columna = cursor.columnNumber() + 1

        # label permanente
        if hasattr(self, "lbl_pos"):
            self.lbl_pos.setText(f"Línea: {linea} | Columna: {columna}")
        else:
            # fallback
            self.barra_estado.showMessage(f"Línea: {linea} | Columna: {columna}")
