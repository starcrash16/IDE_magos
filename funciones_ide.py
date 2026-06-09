"""
funciones_ide.py
Funciones de manejo de archivos y ejecución del compilador para CompiladorIDE.
Se importan en main.py y se asignan como métodos de la clase.
"""

# QFileDialog: Abre el explorador de archivos para seleccionar un archivo.
# QMessageBox: Muestra mensajes de error o información al usuario.
import subprocess
import json
import os
from PySide6.QtGui import QColor

from PySide6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem


"""
- clear(): Limpia todo el contenido del editor de texto.
- setWindowTitle(texto): Cambia el título de la ventana principal.

Logica:
    Reinicia el editor a un estado vacío, elimina la referencia a cualquier archivo 
    previamente abierto y actualiza el título de la ventana para indicar un nuevo documento.
"""
def nuevo_archivo(self):
    if not _confirmar_perder_cambios_o_guardar(self):
        return

    self.editor.clear()
    self.editor.document().setModified(False)
    self.archivo_actual = None
    self.setWindowTitle("IDE Compiladores - Fase 1 (Nuevo Archivo)")


"""
Metodos:
- getOpenFileName(parent, titulo, dir, filtro): Abre un diálogo para seleccionar archivos existentes.
- setPlainText(contenido): Inserta el texto leído en el editor reemplazando el contenido actual.
- critical(parent, titulo, mensaje): Muestra una ventana de error en caso de fallo.

Logica:
    Muestra el explorador de archivos. El archivo seleccionado se lee con UTF-8, 
    se escribe en el editor y guarda la ruta para facilidad de guardado o ubicarlo
    Ya después definiremos si se puede abrir cualquier tipo de archivo o solo nuestra extensión
"""
def abrir_archivo(self):
    if not _confirmar_perder_cambios_o_guardar(self):
        return

    ruta_archivo, _ = QFileDialog.getOpenFileName(
        self, "Abrir Archivo", "", "Archivos de texto (*.txt);;Todos los archivos (*)"
    )

    if ruta_archivo:
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                contenido = archivo.read()
                self.editor.setPlainText(contenido)

            self.editor.document().setModified(False)
            self.archivo_actual = ruta_archivo
            self.setWindowTitle(f"IDE Compiladores - {ruta_archivo}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo:\n{e}")


"""
Metodos:
- toPlainText(): Extrae todo el texto actualmente escrito en el editor.
- showMessage(texto, tiempo): Muestra una notificación en la barra de estado por los milisegundos indicados.

Logica:
    Verifica si existe una ruta de archivo abierta. Si existe, escribe el contenido del editor en el 
    disco duro. Si no existe (archivo nuevo), redirige la ejecución a la función 'guardar_como_archivo'.
"""
def guardar_archivo(self):
    """Si ya hay un archivo abierto, lo sobreescribe. Si no, se realiza como Guardar como """
    if self.archivo_actual:
        try:
            with open(self.archivo_actual, 'w', encoding='utf-8') as archivo:
                contenido = self.editor.toPlainText()
                archivo.write(contenido)
            # Resetear el estado "modificado": ya no hay cambios pendientes (se acaba de abrir/guardar/limpiar).
            self.editor.document().setModified(False)
            # Se muestra un pequeño mensaje en la barra de estado
            self.barra_estado.showMessage("Archivo guardado exitosamente.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{e}")
    else:
        # Si no hay archivo previo, se realiza como "Guardar como"
        self.guardar_como_archivo()


"""
Metodos:
- getSaveFileName(parent, titulo, dir, filtro): Abre un diálogo para elegir nombre y ubicación de guardado.

Logica:
    Muestra el explorador para crear un archivo nuevo. Si se elige una ruta válida, la establece 
    como la ruta actual del documento y procede a realizar el guardado físico del texto.
"""
def guardar_como_archivo(self):
    # Abre el explorador para elegir dónde y con qué nombre guardar
    ruta_archivo, _ = QFileDialog.getSaveFileName(
        self, "Guardar Como", "", "Archivos de texto (*.txt);;Todos los archivos (*)"
    )

    # Si se elige una ruta válida, se establece como la ruta actual y se guarda el archivo
    if ruta_archivo:
        self.archivo_actual = ruta_archivo
        self.guardar_archivo()
        self.setWindowTitle(f"IDE Compiladores - {ruta_archivo}")


"""
Metodos:
- clear(): Limpia el contenido del editor.

Logica:
    Limpia el área de trabajo del editor, borra la ruta del archivo actual (cerrando la sesión 
    de edición) y restaura el título original de la aplicación.
"""
def cerrar_archivo(self):
    # Limpia la pantalla. 
    # (Para una fase futura, aquí podrías preguntar "¿Desea guardar los cambios?" si el texto fue modificado)
    self.editor.clear()
    self.archivo_actual = None
    self.setWindowTitle("IDE Compiladores - Fase 1")

def _hay_cambios_sin_guardar(self) -> bool:
    """
    True si el documento del editor está modificado (Qt lo trackea)
    o si hay texto y no hay archivo_actual.
    """
    doc = self.editor.document()
    if doc.isModified():
        return True

    # opcional: si hay texto aunque no marque modified
    if self.editor.toPlainText().strip() and not self.archivo_actual:
        return True

    return False


def _confirmar_perder_cambios_o_guardar(self) -> bool:
    """
    Devuelve True si se permite continuar (abrir/nuevo),
    False si el usuario cancela.
    """
    if not _hay_cambios_sin_guardar(self):
        return True

    msg = QMessageBox(self)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Cambios sin guardar")
    msg.setText("Hay cambios sin guardar.")
    msg.setInformativeText("Si continúas, se perderá la información no guardada. ¿Deseas continuar?")
    msg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
    msg.setDefaultButton(QMessageBox.Save)

    r = msg.exec()

    if r == QMessageBox.Save:
        self.guardar_archivo()
        # Si el usuario cancela el diálogo de guardar, no continúes.
        # (guarda_archivo puede terminar sin ruta si el user cancela)
        return not _hay_cambios_sin_guardar(self)

    if r == QMessageBox.Discard:
        return True

    return False  # Cancel


# ══════════════════════════════════════════════════════════════════════════════
# Ejecución del Analizador Léxico (Fase 2)
# ══════════════════════════════════════════════════════════════════════════════

def ejecutar_lexico(self):
    """
    Ejecuta el analizador léxico sobre el archivo actual.
    1. Guarda el archivo (o pide guardarlo si es nuevo).
    2. Invoca lexer.py vía subprocess.run() (comunicación IPC).
    3. Parsea el JSON de stdout.
    4. Llena las tablas de Tokens y Errores.
    """
    # ── Paso 1: Asegurar que el archivo está guardado ────────────────────
    if not self.archivo_actual:
        QMessageBox.warning(
            self, "Archivo no guardado",
            "Debes guardar el archivo antes de ejecutar el análisis léxico."
        )
        self.guardar_como_archivo()
        if not self.archivo_actual:
            return  # El usuario canceló el diálogo de guardar
    else:
        self.guardar_archivo()

    # ── Paso 2: Determinar la ruta del lexer.py ─────────────────────────
    # El compilador vive en la carpeta hermana "compilador"
    ruta_ide = os.path.dirname(os.path.abspath(__file__))
    ruta_lexer = os.path.join(ruta_ide, "compilador", "lexer.py")

    if not os.path.exists(ruta_lexer):
        QMessageBox.critical(
            self, "Error",
            f"No se encontró el analizador léxico en:\n{ruta_lexer}"
        )
        return

    # ── Paso 3: Invocar el lexer vía subprocess (IPC) ───────────────────
    self.barra_estado.showMessage("Ejecutando análisis léxico...", 5000)

    try:
        resultado = subprocess.run(
            ["python", ruta_lexer, self.archivo_actual],
            capture_output=True,
            text=True,
            timeout=30,  # Timeout de seguridad (30 segundos)
        )
    except subprocess.TimeoutExpired:
        QMessageBox.critical(
            self, "Error",
            "El analizador léxico tardó demasiado (timeout de 30s)."
        )
        return
    except Exception as e:
        QMessageBox.critical(
            self, "Error",
            f"Error al ejecutar el analizador léxico:\n{e}"
        )
        return

    # ── Paso 4: Parsear el JSON de stdout ────────────────────────────────
    salida = resultado.stdout.strip()

    if not salida:
        error_stderr = resultado.stderr.strip()
        QMessageBox.critical(
            self, "Error del Lexer",
            f"El analizador léxico no produjo salida.\n\nstderr:\n{error_stderr}"
        )
        return

    try:
        datos = json.loads(salida)
    except json.JSONDecodeError as e:
        QMessageBox.critical(
            self, "Error de formato",
            f"La salida del lexer no es JSON válido:\n{e}\n\nSalida:\n{salida[:500]}"
        )
        return

    lista_tokens = datos.get("tokens", [])
    lista_errores = datos.get("errores", [])

    # ── Paso 5: Llenar la tabla de Tokens ────────────────────────────────
    self.tabla_tokens.setRowCount(0)

    colores_tokens = {
        "PALABRA_RESERVADA": QColor("#ff6b6b"),   # rojo suave
        "IDENTIFICADOR": QColor("#d4d4d4"),       # blanco/gris claro
        "NUMERO_ENTERO": QColor("#b5cea8"),       # verde claro
        "NUMERO_REAL": QColor("#b5cea8"),         # verde claro
        "CADENA": QColor("#ce9178"),              # naranja
        "CARACTER": QColor("#ce9178"),            # naranja
        "OP_ARITMETICO": QColor("#d7ba7d"),       # amarillo
        "OP_RELACIONAL": QColor("#4fc1ff"),       # azul claro
        "OP_LOGICO": QColor("#c586c0"),           # morado
        "ASIGNACION": QColor("#ffd700"),          # dorado
        "PARENTESIS_IZQ": QColor("#f5f5f5"),
        "PARENTESIS_DER": QColor("#f5f5f5"),
        "LLAVE_IZQ": QColor("#f5f5f5"),
        "LLAVE_DER": QColor("#f5f5f5"),
        "COMA": QColor("#f5f5f5"),
        "PUNTO_Y_COMA": QColor("#f5f5f5"),
        "DOS_PUNTOS": QColor("#f5f5f5"),
        "INSERCION": QColor("#4ec9b0"),
        "EXTRACCION": QColor("#4ec9b0"),
    }

    for token in lista_tokens:
        fila = self.tabla_tokens.rowCount()
        self.tabla_tokens.insertRow(fila)

        tipo_token = token.get("tipo", "")
        color = colores_tokens.get(tipo_token, QColor("#f5f5f5"))

        item_linea = QTableWidgetItem(str(token.get("linea", "")))
        item_columna = QTableWidgetItem(str(token.get("columna", "")))
        item_tipo = QTableWidgetItem(tipo_token)
        item_lexema = QTableWidgetItem(token.get("lexema", ""))

        item_linea.setForeground(color)
        item_columna.setForeground(color)
        item_tipo.setForeground(color)
        item_lexema.setForeground(color)

        self.tabla_tokens.setItem(fila, 0, item_linea)
        self.tabla_tokens.setItem(fila, 1, item_columna)
        self.tabla_tokens.setItem(fila, 2, item_tipo)
        self.tabla_tokens.setItem(fila, 3, item_lexema)

    self.tabla_tokens.resizeColumnsToContents()

    # ── Paso 6: Llenar la tabla de Errores ───────────────────────────────
    self.lista_errores.setRowCount(0)  # Limpiar filas existentes

    for error in lista_errores:
        fila = self.lista_errores.rowCount()
        self.lista_errores.insertRow(fila)
        self.lista_errores.setItem(fila, 0, QTableWidgetItem("Léxico"))
        self.lista_errores.setItem(fila, 1, QTableWidgetItem(str(error.get("linea", ""))))
        self.lista_errores.setItem(fila, 2, QTableWidgetItem(str(error.get("columna", ""))))
        self.lista_errores.setItem(fila, 3, QTableWidgetItem(error.get("descripcion", "")))

    # Ajustar ancho de columnas al contenido
    self.lista_errores.resizeColumnsToContents()

    # ── Paso 7: Mostrar la pestaña correspondiente ───────────────────────
    if lista_errores:
        # Si hay errores, ir a la pestaña de Errores
        indice_errores = self.tabs_resultados.indexOf(self.lista_errores)
        self.tabs_resultados.setCurrentIndex(indice_errores)
        self.barra_estado.showMessage(
            f"Análisis léxico completado: {len(lista_tokens)} tokens, {len(lista_errores)} error(es)", 5000
        )
    else:
        # Si no hay errores, ir a la pestaña de Tokens
        indice_tokens = self.tabs_resultados.indexOf(self.tabla_tokens)
        self.tabs_resultados.setCurrentIndex(indice_tokens)
        self.barra_estado.showMessage(
            f"Análisis léxico completado: {len(lista_tokens)} tokens, sin errores ✓", 5000
        )


# ══════════════════════════════════════════════════════════════════════════════
# Ejecución del Analizador Sintáctico (Fase 3)
# ══════════════════════════════════════════════════════════════════════════════

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtGui import QFont
from arbol_grafico import color_para

def _populate_tree_widget(parent_item, node):
    """Convierte un nodo AST (dict) a QTreeWidgetItem coloreado (una columna)."""
    if not node:
        return

    tipo = str(node.get("type", ""))
    valor = node.get("value")
    linea = node.get("line")

    # Etiqueta: TIPO  valor  · L#   (todo en una sola columna, como la referencia)
    etiqueta = tipo
    if valor is not None:
        etiqueta += f"  {valor}"
    if linea:
        etiqueta += f"   · L{linea}"

    item = QTreeWidgetItem(parent_item)
    item.setText(0, etiqueta)

    # Color del texto según el tipo de nodo
    _bg, fg = color_para(tipo)
    item.setForeground(0, QColor(fg))

    for child in node.get("children", []):
        _populate_tree_widget(item, child)


def ejecutar_sintactico(self):
    """
    Ejecuta el analizador sintáctico sobre el archivo actual.
    1. Guarda el archivo (o pide guardarlo si es nuevo).
    2. Invoca parser.py vía subprocess.run() (comunicación IPC).
    3. Parsea el JSON de stdout.
    4. Muestra el AST en la pestaña Árbol Sintáctico.
    5. Agrega errores sintácticos y léxicos a la tabla de Errores.
    """
    # ── Paso 1: Asegurar que el archivo está guardado ────────────────────
    if not self.archivo_actual:
        QMessageBox.warning(
            self, "Archivo no guardado",
            "Debes guardar el archivo antes de ejecutar el análisis sintáctico."
        )
        self.guardar_como_archivo()
        if not self.archivo_actual:
            return  # El usuario canceló el diálogo de guardar
    else:
        self.guardar_archivo()

    # ── Paso 2: Determinar la ruta del parser.py ─────────────────────────
    ruta_ide = os.path.dirname(os.path.abspath(__file__))
    ruta_parser = os.path.join(ruta_ide, "compilador", "parser.py")

    if not os.path.exists(ruta_parser):
        QMessageBox.critical(
            self, "Error",
            f"No se encontró el analizador sintáctico en:\n{ruta_parser}"
        )
        return

    # ── Paso 3: Invocar el parser vía subprocess (IPC) ───────────────────
    self.barra_estado.showMessage("Ejecutando análisis sintáctico...", 5000)

    try:
        resultado = subprocess.run(
            ["python", ruta_parser, self.archivo_actual],
            capture_output=True,
            text=True,
            timeout=30,  # Timeout de seguridad (30 segundos)
        )
    except subprocess.TimeoutExpired:
        QMessageBox.critical(
            self, "Error",
            "El analizador sintáctico tardó demasiado (timeout de 30s)."
        )
        return
    except Exception as e:
        QMessageBox.critical(
            self, "Error",
            f"Error al ejecutar el analizador sintáctico:\n{e}"
        )
        return

    # ── Paso 4: Parsear el JSON de stdout ────────────────────────────────
    salida = resultado.stdout.strip()

    if not salida:
        error_stderr = resultado.stderr.strip()
        QMessageBox.critical(
            self, "Error del Parser",
            f"El analizador sintáctico no produjo salida.\n\nstderr:\n{error_stderr}"
        )
        return

    try:
        datos = json.loads(salida)
    except json.JSONDecodeError as e:
        QMessageBox.critical(
            self, "Error de formato",
            f"La salida del parser no es JSON válido:\n{e}\n\nSalida:\n{salida[:500]}"
        )
        return

    ast_dict = datos.get("ast")
    errores_lexicos = datos.get("errores_lexicos", [])
    errores_sintacticos = datos.get("errores_sintacticos", [])

    # ── Paso 5: Mostrar el AST en la pestaña Árbol Sintáctico ────────────
    # 5a. Árbol lista (QTreeWidget coloreado)
    self.arbol_sintactico.clear()

    if ast_dict:
        _populate_tree_widget(self.arbol_sintactico, ast_dict)
        self.arbol_sintactico.expandAll()
    else:
        err_item = QTreeWidgetItem(self.arbol_sintactico)
        err_item.setText(0, "⚠ No se pudo construir el árbol sintáctico.")
        err_item.setForeground(0, QColor("#ff6b6b"))

    # 5b. Árbol gráfico (cajas con zoom)
    self.arbol_grafico.dibujar(ast_dict)

    # ── Paso 6: Llenar la tabla de Errores ───────────────────────────────
    self.lista_errores.setRowCount(0)

    for error in errores_lexicos:
        fila = self.lista_errores.rowCount()
        self.lista_errores.insertRow(fila)
        self.lista_errores.setItem(fila, 0, QTableWidgetItem("Léxico"))
        self.lista_errores.setItem(fila, 1, QTableWidgetItem(str(error.get("linea", ""))))
        self.lista_errores.setItem(fila, 2, QTableWidgetItem(str(error.get("columna", ""))))
        self.lista_errores.setItem(fila, 3, QTableWidgetItem(error.get("descripcion", "")))

    for error in errores_sintacticos:
        fila = self.lista_errores.rowCount()
        self.lista_errores.insertRow(fila)
        # ✅ implemented by agent — labeled [SINTÁCTICO] and using columna
        self.lista_errores.setItem(fila, 0, QTableWidgetItem("[SINTÁCTICO]"))
        self.lista_errores.setItem(fila, 1, QTableWidgetItem(str(error.get("linea", ""))))
        self.lista_errores.setItem(fila, 2, QTableWidgetItem(str(error.get("columna", ""))))
        self.lista_errores.setItem(fila, 3, QTableWidgetItem(error.get("descripcion", "")))

    self.lista_errores.resizeColumnsToContents()

    # ── Paso 7: Mostrar la pestaña correspondiente ───────────────────────
    total_errores = len(errores_lexicos) + len(errores_sintacticos)

    if total_errores > 0:
        # Si hay errores, ir a la pestaña de Errores
        indice_errores = self.tabs_resultados.indexOf(self.lista_errores)
        self.tabs_resultados.setCurrentIndex(indice_errores)
        self.barra_estado.showMessage(
            f"Análisis sintáctico completado: {total_errores} error(es)", 5000
        )
    else:
        # Si no hay errores, ir a la pestaña de Árbol Sintáctico
        indice_arbol = self.tabs_resultados.indexOf(self.tab_arbol)
        self.tabs_resultados.setCurrentIndex(indice_arbol)
        self.barra_estado.showMessage(
            "Análisis sintáctico completado: sin errores ✓", 5000
        )