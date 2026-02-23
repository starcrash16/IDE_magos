"""
Contiene toda la lógica de creación y configuración de widgets.
Se usa como clase base en main.py:
    class CompiladorIDE(SetupInterfaz, QMainWindow)
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QTabWidget,
                               QTableWidget, QToolBar, QStatusBar)
from PySide6.QtGui import QAction


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

    def inicializar_interfaz(self):
        # 1. Configurar Menús y Barra de Herramientas
        self.crear_menus()
        self.crear_barra_herramientas()

        # Widget Central Principal
        widget_central = QWidget()
        layout_principal = QVBoxLayout(widget_central)
        self.setCentralWidget(widget_central)

        # 2. Editor de Texto 
        # (Requerimiento 3.1)
        self.editor = QTextEdit()
        # Conectar el movimiento del cursor a la barra de estado
        self.editor.cursorPositionChanged.connect(self.actualizar_posicion_cursor)
        layout_principal.addWidget(self.editor, stretch=6)

        # 3. Paneles de Resultados 
        # (Requerimientos 3.2 al 3.8)
        self.tabs_resultados = QTabWidget()
        self.configurar_paneles_resultados()
        layout_principal.addWidget(self.tabs_resultados, stretch=4)

        # 4. Barra de Estado 
        # (Requerimiento 3.1.c - Visualización de columna y línea)
        self.barra_estado = QStatusBar()
        self.setStatusBar(self.barra_estado)
        self.actualizar_posicion_cursor()

    # ─── Menús ────────────────────────────────────────────────────────────────

    def crear_menus(self):
        """Crea la barra de menús superior y configura sus acciones."""
        barra_menus = self.menuBar()

        # Contiene funciones básicas como Nuevo, Abrir y Guardar
        menu_archivo = barra_menus.addMenu("Archivo")

        # Acción para crear un nuevo archivo
        accion_nuevo = QAction("Nuevo", self)
        accion_nuevo.triggered.connect(self.nuevo_archivo)
        menu_archivo.addAction(accion_nuevo)

        # Acción para abrir un archivo existente desde el disco
        accion_abrir = QAction("Abrir", self)
        accion_abrir.triggered.connect(self.abrir_archivo)
        menu_archivo.addAction(accion_abrir)

        # Acción para guardar los cambios en el archivo actual
        accion_guardar = QAction("Guardar", self)
        accion_guardar.triggered.connect(self.guardar_archivo)
        menu_archivo.addAction(accion_guardar)

        # Acción para guardar el contenido actual con un nombre nuevo
        accion_guardar_como = QAction("Guardar como", self)
        accion_guardar_como.triggered.connect(self.guardar_como_archivo)
        menu_archivo.addAction(accion_guardar_como)

        # Separador visual (opcional si se desea en el futuro) y acción de salir
        accion_salir = QAction("Salir", self)
        accion_salir.triggered.connect(self.close)
        menu_archivo.addAction(accion_salir)

        # Menú Compilar
        # Define el acceso a las fases principales del proceso de compilación
        menu_compilar = barra_menus.addMenu("Compilar")
        fases = [
            "Análisis Léxico", 
            "Análisis Sintáctico", 
            "Análisis Semántico",
            "Generación de Código Intermedio", 
            "Ejecución"
        ]
        
        # Generar las opciones del menú de forma iterativa, nomas para ahorrar código pa
        for fase in fases:
            act = QAction(fase, self)
            menu_compilar.addAction(act)

    # ─── Barra de Herramientas ────────────────────────────────────────────────

    def crear_barra_herramientas(self):
        # Botones de acceso rápido 
        # (Requerimiento 2.2)
        toolbar = QToolBar("Acceso Rápido")
        self.addToolBar(toolbar)

        btn_lexico     = QAction("Ejecutar Léxico", self)
        btn_sintactico = QAction("Ejecutar Sintáctico", self)
        btn_ejecutar   = QAction("Ejecutar Todo", self)

        toolbar.addAction(btn_lexico)
        toolbar.addAction(btn_sintactico)
        toolbar.addAction(btn_ejecutar)

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
        # Crear los componentes para cada pestaña solicitada
        self.tabla_tokens = QTableWidget(0, 3)
        self.tabla_tokens.setHorizontalHeaderLabels(["Línea", "Token", "Lexema"])

        # Tabla para la Tabla de Símbolos (Identificadores y sus propiedades)
        self.tabla_simbolos = QTableWidget(0, 4)
        self.tabla_simbolos.setHorizontalHeaderLabels(["ID", "Tipo", "Valor", "Línea"])

        # Tabla para mostrar errores detectados durante cualquier fase
        self.lista_errores = QTableWidget(0, 4)
        self.lista_errores.setHorizontalHeaderLabels(["Tipo", "Línea", "Columna", "Descripción"])

        # 2. Configuración de Áreas de Texto (Para representaciones visuales o salidas de texto)
        # Panel para el dibujo o representación del Árbol Sintáctico
        self.arbol_sintactico = QTextEdit()
        self.arbol_sintactico.setReadOnly(True)

        # Panel para mostrar el resultado de las validaciones semánticas
        self.analisis_semantico = QTextEdit()
        self.analisis_semantico.setReadOnly(True)

        # Panel para el código de tres direcciones o cuádruplos (Código Intermedio)
        self.codigo_intermedio = QTextEdit()
        self.codigo_intermedio.setReadOnly(True)

        # Panel para la consola de salida (Resultado de la ejecución del programa)
        self.consola_ejecucion = QTextEdit()
        self.consola_ejecucion.setReadOnly(True)

        # Agregar las pestañas al widget 
        # (Requerimiento 3)
        self.tabs_resultados.addTab(self.tabla_tokens,      "Tokens")
        self.tabs_resultados.addTab(self.arbol_sintactico,  "Árbol Sintáctico")
        self.tabs_resultados.addTab(self.analisis_semantico,"Semántica")
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
        # Obtener la posición actual del cursor en el editor
        cursor = self.editor.textCursor()
        linea   = cursor.blockNumber() + 1
        columna = cursor.columnNumber() + 1
        self.barra_estado.showMessage(f"Línea: {linea} | Columna: {columna}")
