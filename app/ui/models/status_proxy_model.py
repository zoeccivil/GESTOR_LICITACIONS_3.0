from PyQt6.QtCore import QSortFilterProxyModel, Qt

ROLE_RECORD_ROLE = Qt.ItemDataRole.UserRole + 1002


class StatusFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy con filtros tolerantes:
    - _filter_estado puede ser str o colección (set/list/tuple) de cadenas.
    - Filtros de empresa y lote robustos a datos faltantes.
    - Evita llamar .lower() sobre tipos no cadena.
    """

    def __init__(self, show_finalizadas: bool = False, status_engine=None, parent=None):
        super().__init__(parent)
        self.show_finalizadas = show_finalizadas
        self.status_engine = status_engine
        self._search_text = ""
        self._filter_estado = "Todos"      # str | Iterable[str]
        self._filter_empresa = "Todas"     # str | Iterable[str]
        self._filter_lote = ""
        self._filter_lote_contains = ""

    # ---------- Setters de filtros ----------
    def set_search_text(self, text):
        self._search_text = text or ""
        self.invalidateFilter()

    def set_filter_estado(self, estado):
        """
        estado: str o colección de cadenas. 'Todos' desactiva el filtro.
        """
        self._filter_estado = estado if estado not in (None, "") else "Todos"
        self.invalidateFilter()

    def set_filter_empresa(self, empresa):
        """
        empresa: str (nombre) o colección; 'Todas' desactiva el filtro.
        """
        self._filter_empresa = empresa if empresa not in (None, "") else "Todas"
        self.invalidateFilter()

    def set_filter_lote(self, lote: str):
        self._filter_lote = (lote or "").strip()
        self.invalidateFilter()

    def set_filter_lote_contains(self, text: str):
        self._filter_lote_contains = (text or "").strip()
        self.invalidateFilter()

    # ---------- Utilidades internas ----------
    @staticmethod
    def _to_text(val) -> str:
        return ("" if val is None else str(val)).strip()

    @staticmethod
    def _to_lower(val) -> str:
        return StatusFilterProxyModel._to_text(val).lower()

    @staticmethod
    def _iter_lower(it) -> list[str]:
        try:
            return [StatusFilterProxyModel._to_lower(v) for v in it]
        except TypeError:
            # no iterable
            return [StatusFilterProxyModel._to_lower(it)]

    # ---------- Filtro principal ----------
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return True

        index = model.index(source_row, 0, source_parent)
        lic = model.data(index, role=ROLE_RECORD_ROLE)
        if lic is None:
            return False

        # Filtrado por activas/finalizadas (si hay engine)
        if self.status_engine is not None:
            try:
                if self.show_finalizadas:
                    if not self.status_engine.is_finalizada(lic):
                        return False
                else:
                    if self.status_engine.is_finalizada(lic):
                        return False
            except Exception:
                # si el engine falla, no bloquear el registro
                pass

        # Filtrado por estado (acepta str o colección)
        filtro_estado = self._filter_estado
        if filtro_estado and self._to_text(filtro_estado).lower() != "todos":
            estado_txt = self._to_lower(getattr(lic, "estado", None))
            if isinstance(filtro_estado, (set, list, tuple)):
                opciones = [s for s in self._iter_lower(filtro_estado) if s]
                if opciones and not any(opt in estado_txt for opt in opciones):
                    return False
            else:
                needle = self._to_lower(filtro_estado)
                if needle and needle not in estado_txt:
                    return False

        # Filtrado por empresa (acepta str o colección)
        filtro_empresa = self._filter_empresa
        if filtro_empresa and self._to_text(filtro_empresa).lower() != "todas":
            empresas = (
                getattr(lic, "empresas_nuestras", None)
                or getattr(lic, "empresas", None)
                or []
            )
            nombres = []
            for e in empresas:
                n = getattr(e, "nombre", None) or (e if isinstance(e, str) else None)
                if n:
                    nombres.append(self._to_lower(n))

            if isinstance(filtro_empresa, (set, list, tuple)):
                needles = [s for s in self._iter_lower(filtro_empresa) if s]
                # Pasa si al menos uno de los filtros aparece completo en la lista
                if needles and not any(nd in nombres for nd in needles):
                    return False
            else:
                needle = self._to_lower(filtro_empresa)
                if needle and needle not in nombres:
                    return False

        # Filtrado por lote exacto
        if self._filter_lote:
            lotes = getattr(lic, "lotes", None) or []
            lote_needle = self._to_lower(self._filter_lote)
            if not any(
                self._to_lower(getattr(l, "numero", None) if not isinstance(l, str) else l) == lote_needle
                for l in lotes
            ):
                return False

        # Filtrado por lote contiene (más flexible)
        if self._filter_lote_contains:
            lotes = getattr(lic, "lotes", None) or []
            sub = self._to_lower(self._filter_lote_contains)
            if not any(
                sub in self._to_lower(getattr(l, "numero", None) if not isinstance(l, str) else l)
                for l in lotes
            ):
                return False

        # Filtrado por texto de búsqueda (nombre o código)
        if self._search_text:
            texto = self._to_lower(self._search_text)
            nombre = self._to_lower(getattr(lic, "nombre_proceso", "") or getattr(lic, "nombre", ""))
            codigo = self._to_lower(getattr(lic, "numero_proceso", "") or getattr(lic, "numero", ""))
            if texto not in nombre and texto not in codigo:
                return False

        return True