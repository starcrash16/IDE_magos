import sys
# Importamos las clases QApplication y QMainWindow del módulo PySide6.QtWidgets 
# QApplication: Gestiona el bucle de eventos de la aplicación.
# QMainWindow: Proporciona la estructura básica de una ventana principal (menús, barra de estado, etc.)
from PySide6.QtWidgets import QApplication, QMainWindow
# Clase que contiene la lógica de construcción de la interfaz gráfica (widgets, menús, paneles)
from ui_setup import SetupInterfaz

# Módulo de acciones sobre archivos (nuevo, abrir, guardar, cerrar)
from funciones_ide import (
    nuevo_archivo,
    abrir_archivo,
    guardar_archivo,
    guardar_como_archivo,
)

class CompiladorIDE(SetupInterfaz, QMainWindow):
    """
    Ventana principal del IDE de Compiladores.
    La clase hereda de:
    Las acciones de archivo se inyectan como métodos desde funciones_ide.py.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDE Compiladores - Fase 1")
        self.resize(1200, 800)
        self.archivo_actual = None
        # Definido en SetupInterfaz
        self.inicializar_interfaz()   


# ── Acciones de archivo como métodos de la clase ─────────────────────────────

CompiladorIDE.nuevo_archivo        = nuevo_archivo
CompiladorIDE.abrir_archivo        = abrir_archivo
CompiladorIDE.guardar_archivo      = guardar_archivo
CompiladorIDE.guardar_como_archivo = guardar_como_archivo

# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = CompiladorIDE()
    ventana.show()
    sys.exit(app.exec())