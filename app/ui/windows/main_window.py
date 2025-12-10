from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, QSettings, QByteArray, QRect, QTimer
from PyQt6.QtGui import QGuiApplication, QAction, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QMenuBar, QStatusBar,
    QMessageBox, QToolBar, QPushButton, QApplication, QDialog, QStyle
)

from app.core.models import Licitacion
from app.core.db_adapter import DatabaseAdapter

from app.core.logic.status_engine import DefaultStatusEngine
from app.ui.models.licitaciones_table_model import LicitacionesTableModel
from app.ui.windows.dashboard_window import DashboardWindow
from app.ui.views.dashboard_widget import DashboardWidget

try:
    from app.ui.windows.reporte_window import ReportWindow
except Exception:
    ReportWindow = None

from app.ui.dialogs.dialogo_gestionar_instituciones import DialogoGestionarInstituciones
from app.ui.dialogs.dialogo_gestionar_empresas import DialogoGestionarEmpresas

# Catálogos opcionales
try:
    from app.ui.dialogs.dialogo_gestionar_documentos_maestros import DialogoGestionarDocumentos    as DialogoGestionarDocumentos
except Exception:
    DialogoGestionarDocumentos = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_gestionar_competidores import DialogoGestionarCompetidores
except Exception:
    DialogoGestionarCompetidores = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_gestionar_responsables import DialogoGestionarResponsables
except Exception:
    DialogoGestionarResponsables = None  # type: ignore

# Nuevos diálogos de funcionalidad expandida
try:
    from app.ui.dialogs.dialogo_historial import DialogoHistorial, DialogoHistorialCompleto
except Exception:
    DialogoHistorial = None  # type: ignore
    DialogoHistorialCompleto = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_tareas import DialogoGestionarTareas
except Exception:
    DialogoGestionarTareas = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_reportes import DialogoReportes
except Exception:
    DialogoReportes = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_plantillas import DialogoPlantillas
except Exception:
    DialogoPlantillas = None  # type: ignore
try:
    from app.ui.dialogs.dialogo_importar import DialogoImportarDatos
except Exception:
    DialogoImportarDatos = None  # type: ignore

# Gestor de temas (auto y switch)
from app.ui.theme.theme_manager import (
    apply_theme_from_settings, list_themes, apply_theme_by_id, save_theme_selection, current_theme_id
)

# JSON settings helpers
from app.core.app_settings import get_window_state, set_window_state
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from app.ui.windows.licitation_details_window import LicitationDetailsWindow
from app.core.models import Licitacion


class MainWindow(QMainWindow):
    def __init__(self, db_client=None, parent=None):
        super().__init__(parent)

        # Note: Theme is now applied globally in main.py using Titanium Construct
        # The old theme system has been disabled

        self.db: DatabaseAdapter | None = None
        self._settings = QSettings("Zoeccivil", "Licitaciones")
        self.status_engine = DefaultStatusEngine()
        self.licitaciones_model: LicitacionesTableModel | None = None
        self.dashboard_view: DashboardWindow | None = None

        self._create_menubar()
        self._create_toolbar()
        self.setStatusBar(QStatusBar(self))
        self._build_welcome()

        self.setWindowTitle("Gestor de Licitaciones")
        self.resize(1200, 760)

        self._update_actions_enabled(False)
        self._restore_geometry_from_json_then_qsettings()
        self._initialize_database(db_client)

    # ---------------------- UI básica ----------------------
    def _build_welcome(self):
        """Construye la pantalla de bienvenida."""
        import os
        backend = os.getenv("APP_DB_BACKEND", "firestore")
        
        self.welcome = QWidget(self)
        layout = QVBoxLayout(self.welcome)
        
        if backend == "firestore":
            message = (
                "Bienvenido al Gestor de Licitaciones.\n\n"
                "La aplicación está conectada a Firebase Firestore.\n"
                "Configura las credenciales en el archivo .env."
            )
        elif backend == "sqlite":
            message = (
                "Bienvenido al Gestor de Licitaciones.\n\n"
                "La aplicación está usando SQLite local.\n"
                "Los datos se guardan en el archivo configurado en .env."
            )
        elif backend == "mysql":
            message = (
                "Bienvenido al Gestor de Licitaciones.\n\n"
                "La aplicación está conectada a MySQL.\n"
                "Configura la conexión en el archivo .env."
            )
        else:
            message = "Bienvenido al Gestor de Licitaciones."
        
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; color: gray;")
        layout.addWidget(lbl)
        self.setCentralWidget(self.welcome)

    def _create_menubar(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Archivo
        m_archivo = menubar.addMenu("Archivo")
        self.act_sel_crear_db = m_archivo.addAction("Seleccionar/Crear Base de Datos…", self._accion_seleccionar_o_crear_db)
        self.act_backup = m_archivo.addAction("Crear Copia de Seguridad…", self._accion_backup_db)
        self.act_restore = m_archivo.addAction("Restaurar desde Copia…", self._accion_restore_db)
        m_archivo.addSeparator()
        self.act_salir = m_archivo.addAction("Salir", self.close)

        # Ver menu (theme menu disabled - using Titanium Construct exclusively)
        m_ver = menubar.addMenu("Ver")
        # Theme switching disabled - now using Titanium Construct theme exclusively
        # self._menu_tema = m_ver.addMenu("Tema")
        # self._build_theme_menu()

        # Dashboards
        m_dashboards = menubar.addMenu("Dashboards")
        self.act_global_dashboard = m_dashboards.addAction("Dashboard Global (Analítico)")
        self.act_global_dashboard.triggered.connect(self._abrir_dashboard_global)

        # Reportes
        m_reportes = menubar.addMenu("Reportes")
        self.act_reporte_global = m_reportes.addAction("Reporte Global…", self._abrir_reporte_global)
        self.act_reporte_sel = m_reportes.addAction("Reporte de Licitación Seleccionada…", self._abrir_reporte_de_seleccionada)
        m_reportes.addSeparator()
        self.act_reportes_kpis = m_reportes.addAction("📊 Dashboard de KPIs y Reportes", self._abrir_reportes_kpis)
        
        # Tareas y Auditoría (nuevo menú)
        m_gestion = menubar.addMenu("Gestión")
        self.act_tareas = m_gestion.addAction("📋 Gestionar Tareas", self._abrir_gestion_tareas)
        self.act_historial = m_gestion.addAction("📜 Historial de Auditoría", self._abrir_historial_completo)
        m_gestion.addSeparator()
        self.act_plantillas = m_gestion.addAction("📝 Gestionar Plantillas", self._abrir_plantillas)
        self.act_importar = m_gestion.addAction("📂 Importar Datos", self._abrir_importar_datos)

        # Catálogos
        m_catalogos = menubar.addMenu("Catálogos")
        self.act_instituciones = m_catalogos.addAction("Gestionar Instituciones", self._abrir_gestor_instituciones)
        self.act_empresas = m_catalogos.addAction("Gestionar Empresas", self._abrir_gestor_empresas)
        self.act_documentos = m_catalogos.addAction("Gestionar Documentos", self._abrir_gestor_documentos)
        self.act_competidores = m_catalogos.addAction("Gestionar Competidores", self._abrir_gestor_competidores)
        self.act_responsables = m_catalogos.addAction("Gestionar Responsables", self._abrir_gestor_responsables)

    def _build_theme_menu(self):
        app = QApplication.instance()
        if not app:
            return

        # Evita usar 'Dict' (sin importar typing); usa un dict normal
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions = {}  # id -> QAction

        themes = list_themes()
        current_id = current_theme_id(default="dim_theme")

        if not themes:
            # Fallback: al menos una acción dummy
            act = self._menu_tema.addAction("Tema por defecto (dim_theme)")
            act.setCheckable(True)
            act.setChecked(True)
            act.triggered.connect(lambda: None)
            return

        for info in themes:
            act = QAction(info.title, self)
            act.setCheckable(True)
            act.setData(info.id)
            if info.id == current_id:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, tid=info.id: self._on_switch_theme(tid))
            self._theme_group.addAction(act)
            self._menu_tema.addAction(act)
        self._theme_actions[info.id] = act

    def _on_switch_theme(self, theme_id: str):
        app = QApplication.instance()
        if not app:
            return
        ok = apply_theme_by_id(app, theme_id)
        if not ok:
            QMessageBox.warning(self, "Tema", f"No se pudo aplicar el tema '{theme_id}'.")
            return
        save_theme_selection(theme_id)
        # Actualiza checks en el menú
        for tid, act in self._theme_actions.items():
            act.setChecked(tid == theme_id)

    def _create_toolbar(self):
        tb = QToolBar("Acciones Principales", self)
        self.addToolBar(tb)
        style = self.style()

        self.btn_nueva_lic = QPushButton(" Nueva Licitación")
        self.btn_nueva_lic.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_nueva_lic.setToolTip("Crear una nueva licitación")
        self.btn_nueva_lic.setProperty("class", "primary")
        self.btn_nueva_lic.clicked.connect(self._accion_nueva_licitacion)
        tb.addWidget(self.btn_nueva_lic)

        self.btn_editar_ver_lic = QPushButton(" Editar/Ver Seleccionada")
        self.btn_editar_ver_lic.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.btn_editar_ver_lic.setToolTip("Abrir detalles de la licitación seleccionada")
        self.btn_editar_ver_lic.clicked.connect(self._accion_editar_licitacion_seleccionada)
        tb.addWidget(self.btn_editar_ver_lic)

    def _update_actions_enabled(self, enabled: bool):
        for act in (
            self.act_backup, self.act_restore, self.act_global_dashboard,
            self.act_reporte_global, self.act_reporte_sel, self.act_reportes_kpis,
            self.act_tareas, self.act_historial, self.act_plantillas, self.act_importar,
            self.act_instituciones, self.act_empresas,
            self.act_documentos, self.act_competidores, self.act_responsables,
        ):
            act.setEnabled(enabled)
        self.btn_nueva_lic.setEnabled(enabled)
        self.btn_editar_ver_lic.setEnabled(enabled)

    # ---------------------- Firestore bootstrap ----------------------
    def _initialize_database(self, db_client):
        """Inicializa el adaptador de base de datos según la configuración."""
        from app.core.db_adapter_selector import get_database_adapter
        
        try:
            self.db = get_database_adapter(db_client=db_client)
            self.db.open()
        except Exception as exc:
            import os
            backend = os.getenv("APP_DB_BACKEND", "firestore")
            QMessageBox.critical(
                self, 
                "Error de Base de Datos", 
                f"No se pudo inicializar la conexión al backend '{backend}':\n{exc}"
            )
            return

        self._ensure_model()
        self._load_licitaciones_iniciales()
        self._suscribirse_a_actualizaciones()
        self._update_actions_enabled(True)
        self._ver_dashboard_list_view()

    def _ensure_model(self):
        if self.licitaciones_model is None:
            self.licitaciones_model = LicitacionesTableModel(parent=self, status_engine=self.status_engine)

    def _suscribirse_a_actualizaciones(self):
        if not self.db:
            return

        def _apply(licitaciones: List[Licitacion]):
            def _update():
                if not self.licitaciones_model:
                    return
                self.licitaciones_model.set_rows(licitaciones)
                if self.dashboard_view:
                    self.dashboard_view._populate_filter_values()
                    self.dashboard_view._apply_filters_to_both()

            QTimer.singleShot(0, _update)

        self.db.subscribe_to_licitaciones(_apply)

    def _load_licitaciones_iniciales(self):
        """Carga las licitaciones iniciales desde la base de datos."""
        if not self.db or not self.licitaciones_model:
            return
        import os
        backend = os.getenv("APP_DB_BACKEND", "firestore")
        
        licitaciones = self.db.load_all_licitaciones() or []
        self.licitaciones_model.set_rows(licitaciones)
        
        backend_names = {
            "firestore": "Firebase Firestore",
            "sqlite": "SQLite Local",
            "mysql": "MySQL"
        }
        backend_display = backend_names.get(backend, backend)
        self.statusBar().showMessage(f"Conectado a {backend_display}", 8000)

    # ---------------------- Backup / Restore ----------------------
    def _accion_backup_db(self):
        QMessageBox.information(
            self,
            "Copia de Seguridad",
            "La base de datos ahora vive en Firebase Firestore. Usa las herramientas de copias de seguridad de Firebase desde la consola web.",
        )

    def _accion_restore_db(self):
        QMessageBox.information(
            self,
            "Restaurar",
            "La restauración de datos debe gestionarse desde Firebase Firestore (exportaciones/importaciones).",
        )

    def _accion_seleccionar_o_crear_db(self):
        QMessageBox.information(
            self,
            "Firebase",
            "La aplicación se conecta automáticamente a Firebase Firestore; no es necesario seleccionar archivos locales.",
        )

    # ---------------------- Dashboard listado ----------------------
    def _ver_dashboard_list_view(self):
        if not self.db or not self.licitaciones_model:
            self._build_welcome()
            return

        create = self.dashboard_view is None
        if create:
            self.dashboard_view = DashboardWindow(model=self.licitaciones_model, parent=self, status_engine=self.status_engine)
            self.dashboard_view.detailRequested.connect(self._accion_abrir_licitacion_por_objeto)
        else:
            try:
                licitaciones = self.db.load_all_licitaciones() or []
                self.licitaciones_model.set_rows(licitaciones)
                self.dashboard_view._populate_filter_values()
                self.dashboard_view._apply_filters_to_both()
            except Exception:
                pass

        self.setCentralWidget(self.dashboard_view)

    # ---------------------- Acciones Licitación / Dashboards / Reportes ----------------------
    def _accion_nueva_licitacion(self):
        if not self.db:
            return QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
        lic = Licitacion()
        from app.ui.windows.licitation_details_window import LicitationDetailsWindow
        dlg = LicitationDetailsWindow(self, lic, self.db, self._refresh_dashboard_data)
        dlg.exec()

    def _accion_editar_licitacion_seleccionada(self):
        if not self.db or not self.dashboard_view or not self.centralWidget() == self.dashboard_view:
            return QMessageBox.information(self, "Vista Incorrecta", "El dashboard de listado no está visible.")
        try:
            selected = self.dashboard_view.get_selected_licitacion_object()
        except Exception as e:
            return QMessageBox.warning(self, "Error", f"No se pudo obtener la selección: {e}")
        if not isinstance(selected, Licitacion):
            return QMessageBox.information(self, "Sin Selección", "Selecciona una licitación en la tabla.")
        self._accion_abrir_licitacion_por_id(getattr(selected, "id", None))

    def _accion_abrir_licitacion_por_objeto(self, lic: Licitacion | object):
        if isinstance(lic, Licitacion):
            return self._accion_abrir_licitacion_por_id(getattr(lic, "id", None))

    def _accion_abrir_licitacion_por_id(self, licitacion_id: int | None):
        if not self.db:
            return QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
        if not licitacion_id:
            return
        try:
            lic = self.db.load_licitacion_by_id(licitacion_id)
            if not lic:
                return QMessageBox.warning(self, "No encontrado", f"No se encontró licitación ID {licitacion_id}.")
            from app.ui.windows.licitation_details_window import LicitationDetailsWindow
            dlg = LicitationDetailsWindow(self, lic, self.db, self._refresh_dashboard_data)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la licitación:\n{e}")

    def _abrir_dashboard_global(self):
        if not self.db:
            return QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Dashboard Global - Análisis General")
            dlg.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint |
                               Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(5, 5, 5, 5)
            dashboard_global = DashboardWidget(db=self.db, parent=dlg)
            layout.addWidget(dashboard_global)
            dashboard_global.edit_licitacion_requested.connect(self._accion_abrir_licitacion_por_id)
            try:
                screen_size = self.screen().availableGeometry()
                dlg.resize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.8))
            except Exception:
                dlg.resize(1200, 800)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el Dashboard Global:\n{e}")

    def _abrir_reporte_global(self):
        # Por ahora reutilizamos el dashboard global como reporte visual global
        return self._abrir_dashboard_global()

    def _abrir_reporte_de_seleccionada(self):
        if not self.db:
            return QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
        if ReportWindow is None:
            return QMessageBox.warning(self, "Reportes", "ReportWindow no está disponible.")
        if not self.dashboard_view or not self.centralWidget() == self.dashboard_view:
            return QMessageBox.information(self, "Vista Incorrecta", "Muestra el dashboard de listado para elegir una licitación.")
        try:
            lic = self.dashboard_view.get_selected_licitacion_object()
        except Exception as e:
            return QMessageBox.warning(self, "Reportes", f"No se pudo obtener la selección actual:\n{e}")
        if not isinstance(lic, Licitacion):
            return QMessageBox.information(self, "Reportes", "Selecciona una licitación en el dashboard de listado.")
        try:
            win = ReportWindow(lic, self, start_maximized=True)
            win.show()
        except Exception as e:
            QMessageBox.critical(self, "Reportes", f"No se pudo abrir el reporte:\n{e}")

    # ---------------------- Catálogos ----------------------
    def _abrir_gestor_empresas(self):
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        try:
            dlg = DialogoGestionarEmpresas(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Catálogos", f"No se pudo abrir 'Gestionar Empresas':\n{e}")

    def _abrir_gestor_instituciones(self):
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        try:
            dlg = DialogoGestionarInstituciones(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Catálogos", f"No se pudo abrir 'Gestionar Instituciones':\n{e}")

    def _abrir_gestor_documentos(self):
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoGestionarDocumentos is None:
            QMessageBox.warning(self, "Catálogos", "El gestor de Documentos no está disponible en esta instalación.")
            return
        try:
            dlg = DialogoGestionarDocumentos(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Catálogos", f"No se pudo abrir 'Gestionar Documentos':\n{e}")

    def _abrir_gestor_competidores(self):
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoGestionarCompetidores is None:
            QMessageBox.warning(self, "Catálogos", "El gestor de Competidores no está disponible en esta instalación.")
            return
        try:
            dlg = DialogoGestionarCompetidores(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Catálogos", f"No se pudo abrir 'Gestionar Competidores':\n{e}")

    def _abrir_gestor_responsables(self):
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoGestionarResponsables is None:
            QMessageBox.warning(self, "Catálogos", "El gestor de Responsables no está disponible en esta instalación.")
            return
        try:
            dlg = DialogoGestionarResponsables(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Catálogos", f"No se pudo abrir 'Gestionar Responsables':\n{e}")

    # ---------------------- Nuevas funcionalidades ----------------------
    def _abrir_reportes_kpis(self):
        """Abre el dashboard de KPIs y reportes avanzados."""
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoReportes is None:
            QMessageBox.warning(self, "Reportes", "El módulo de reportes avanzados no está disponible.")
            return
        try:
            dlg = DialogoReportes(self, self.db)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Reportes", f"No se pudo abrir el dashboard de KPIs:\n{e}")

    def _abrir_gestion_tareas(self):
        """Abre el gestor de tareas."""
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoGestionarTareas is None:
            QMessageBox.warning(self, "Tareas", "El módulo de gestión de tareas no está disponible.")
            return
        try:
            dlg = DialogoGestionarTareas(self)
            dlg.exec()
            # Refrescar si hubo cambios
            self._refresh_dashboard_data()
        except Exception as e:
            QMessageBox.critical(self, "Tareas", f"No se pudo abrir el gestor de tareas:\n{e}")

    def _abrir_historial_completo(self):
        """Abre el visor de historial de auditoría completo."""
        if DialogoHistorialCompleto is None:
            QMessageBox.warning(self, "Auditoría", "El módulo de auditoría no está disponible.")
            return
        try:
            dlg = DialogoHistorialCompleto(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Auditoría", f"No se pudo abrir el historial:\n{e}")

    def _abrir_plantillas(self):
        """Abre el gestor de plantillas."""
        if DialogoPlantillas is None:
            QMessageBox.warning(self, "Plantillas", "El módulo de plantillas no está disponible.")
            return
        try:
            dlg = DialogoPlantillas(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Plantillas", f"No se pudo abrir el gestor de plantillas:\n{e}")

    def _abrir_importar_datos(self):
        """Abre el asistente de importación de datos."""
        if not getattr(self, "db", None):
            QMessageBox.information(self, "DB Requerida", "Abre una base de datos primero.")
            return
        if DialogoImportarDatos is None:
            QMessageBox.warning(self, "Importar", "El módulo de importación no está disponible.")
            return
        try:
            from PyQt6.QtWidgets import QInputDialog
            
            # Preguntar qué tipo de datos importar
            tipos = ["lotes", "documentos"]
            tipo, ok = QInputDialog.getItem(
                self, "Importar Datos", 
                "Seleccione el tipo de datos a importar:",
                tipos, 0, False
            )
            
            if not ok:
                return
            
            dlg = DialogoImportarDatos(self, self.db, entity_type=tipo)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                QMessageBox.information(self, "Importación", "Datos importados exitosamente")
                self._refresh_dashboard_data()
        except Exception as e:
            QMessageBox.critical(self, "Importar", f"No se pudo abrir el asistente de importación:\n{e}")

    # ---------------------- Utilidades ----------------------
    def _refresh_dashboard_data(self):
        if self.licitaciones_model and self.db:
            try:
                licitaciones = self.db.load_all_licitaciones() or []
                self.licitaciones_model.set_rows(licitaciones)
                if self.dashboard_view:
                    self.dashboard_view._populate_filter_values()
                    self.dashboard_view._apply_filters_to_both()
            except Exception:
                pass

    def _restore_geometry(self):
        geom = self._settings.value("MainWindow/geometry")
        if isinstance(geom, QByteArray):
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

    # ---------------------- Restaurar/Guardar geometría ----------------------
    def _restore_geometry_from_json_then_qsettings(self):
        """
        Restaura geometría y estado de la ventana priorizando el JSON (licitaciones_config).
        Si no hay datos válidos, intenta QSettings. Como último recurso, mantiene tamaño por defecto.
        """
        try:
            st = get_window_state("MainWindow")
            x, y, w, h = st.get("x", 0), st.get("y", 0), st.get("w", 0), st.get("h", 0)
            maximized = bool(st.get("maximized", False))

            applied = False
            if w > 100 and h > 80:  # umbrales mínimos razonables
                rect = QRect(int(x), int(y), int(w), int(h))
                # Validar que la ventana quede en alguna pantalla visible
                if not self._rect_intersects_any_screen(rect):
                    # centrar en la pantalla principal con el mismo tamaño
                    primary = QGuiApplication.primaryScreen()
                    if primary:
                        avail = primary.availableGeometry()
                        nx = max(avail.x(), avail.x() + (avail.width() - rect.width()) // 2)
                        ny = max(avail.y(), avail.y() + (avail.height() - rect.height()) // 2)
                        rect.moveTo(nx, ny)
                self.setGeometry(rect)
                if maximized:
                    self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
                applied = True

            if not applied:
                # Fallback a QSettings
                geom = self._settings.value("MainWindow/geometry")
                if isinstance(geom, QByteArray):
                    try:
                        self.restoreGeometry(geom)
                        applied = True
                    except Exception:
                        applied = False
            # Si nada aplicó, deja el resize(1200x760) que ya se hizo
        except Exception:
            # No interrumpir el arranque por un detalle de layout
            pass

    def _rect_intersects_any_screen(self, rect: QRect) -> bool:
        try:
            for screen in QGuiApplication.screens():
                if rect.intersects(screen.availableGeometry()):
                    return True
        except Exception:
            pass
        return False

    def _save_window_state_to_json(self):
        """
        Guarda en JSON la geometría (normal) y el estado maximizado de la ventana.
        Si está maximizada, guardamos la geometría 'normal' para restaurar correctamente.
        """
        try:
            is_max = self.isMaximized()
            rect = self.normalGeometry() if is_max else self.geometry()
            set_window_state(
                "MainWindow",
                rect.x(), rect.y(), rect.width(), rect.height(),
                bool(is_max)
            )
        except Exception:
            pass

    # ---------------------- Cierre ----------------------
    def closeEvent(self, event):
        try:
            # Guardar QSettings (retrocompatibilidad)
            self._settings.setValue("MainWindow/geometry", self.saveGeometry())
            # Guardar JSON
            self._save_window_state_to_json()
        finally:
            if self.db:
                try:
                    self.db.close()
                except Exception:
                    pass
            super().closeEvent(event)


    def on_action_nueva_licitacion_triggered(self):
        """
        Handler del menú/toolbar 'Nueva licitación'.
        Abre LicitationDetailsWindow en modo creación con un modelo vacío.
        """
        nueva = Licitacion(
            nombre_proceso="",
            numero_proceso="",
            institucion="",
            empresas_nuestras=[],
            lotes=[],
            documentos_solicitados=[]
        )
        dlg = LicitationDetailsWindow(self, nueva, db_adapter=self.db, refresh_callback=self._refrescar_tabla)
        dlg.saved.connect(self._on_licitacion_saved)
        dlg.exec()

    def on_action_editar_licitacion_triggered(self):
        """
        Handler para editar la licitación seleccionada (por ejemplo, desde un botón 'Editar').
        Si usas doble clic en la tabla, llama este método desde ese evento.
        """
        licitacion = self._get_licitacion_seleccionada()
        if not licitacion:
            QMessageBox.warning(self, "Editar Licitación", "Seleccione una licitación para editar.")
            return
        dlg = LicitationDetailsWindow(self, licitacion, db_adapter=self.db, refresh_callback=self._refrescar_tabla)
        dlg.saved.connect(self._on_licitacion_saved)
        dlg.exec()

    def _on_table_double_clicked(self, index):
        """
        Si tienes una QTableView/QTableWidget con doble clic para editar, enlázalo a este slot
        y reusa el handler de edición.
        """
        self.on_action_editar_licitacion_triggered()

    def _on_licitacion_saved(self, lic):
        """
        Callback opcional al guardar (creación/edición). Ya se invoca _refrescar_tabla
        desde el refresh_callback, pero aquí puedes reaccionar adicionalmente si quieres.
        """
        # Ejemplo: log simple
        try:
            print("Guardada:", getattr(lic, "id", None), getattr(lic, "numero_proceso", ""))
        except Exception:
            pass

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())