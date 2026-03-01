"""
funciones_ide.py
Funciones de manejo de archivos para CompiladorIDE.
Se importan en main.py y se asignan como métodos de la clase.
"""

# QFileDialog: Abre el explorador de archivos para seleccionar un archivo.
# QMessageBox: Muestra mensajes de error o información al usuario.
from PySide6.QtWidgets import QFileDialog, QMessageBox


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