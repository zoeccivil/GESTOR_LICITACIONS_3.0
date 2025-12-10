from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import datetime
import json

from .utils import as_dict


@dataclass
class Lote:
    id: Optional[int] = None
    numero: str = ""
    nombre: str = ""
    monto_base: float = 0.0
    monto_base_personal: float = 0.0
    monto_ofertado: float = 0.0
    participamos: bool = True
    fase_A_superada: bool = True
    ganador_nombre: str = ""
    ganado_por_nosotros: bool = False
    empresa_nuestra: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "numero": self.numero,
            "nombre": self.nombre,
            "monto_base": self.monto_base,
            "monto_base_personal": self.monto_base_personal,
            "monto_ofertado": self.monto_ofertado,
            "participamos": self.participamos,
            "fase_A_superada": self.fase_A_superada,
            "empresa_nuestra": self.empresa_nuestra,
            "ganador_nombre": self.ganador_nombre,
            "ganado_por_nosotros": self.ganado_por_nosotros,
        }


@dataclass
class Oferente:
    nombre: str = ""
    comentario: str = ""
    ofertas_por_lote: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre,
            "comentario": self.comentario,
            "ofertas_por_lote": self.ofertas_por_lote,
        }

    def get_monto_total_ofertado(self, solo_habilitados: bool = False) -> float:
        ofertas = self.ofertas_por_lote
        if solo_habilitados:
            ofertas = [o for o in ofertas if o.get("paso_fase_A", True)]
        return float(sum(o.get("monto", 0) or 0 for o in ofertas))


@dataclass
class Documento:
    id: Optional[int] = None
    codigo: str = ""
    nombre: str = ""
    categoria: str = ""
    comentario: str = ""
    presentado: bool = False
    subsanable: str = "Subsanable"
    ruta_archivo: str = ""
    empresa_nombre: Optional[str] = None
    responsable: str = "Sin Asignar"
    revisado: bool = False
    obligatorio: bool = False
    orden_pliego: Optional[int] = None
    requiere_subsanacion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "comentario": self.comentario,
            "presentado": self.presentado,
            "subsanable": self.subsanable,
            "ruta_archivo": self.ruta_archivo,
            "empresa_nombre": self.empresa_nombre,
            "responsable": self.responsable,
            "revisado": self.revisado,
            "obligatorio": self.obligatorio,
            "orden_pliego": self.orden_pliego,
            "requiere_subsanacion": self.requiere_subsanacion,
        }

    def __str__(self) -> str:
        estado = "✅" if self.presentado else "❌"
        adjunto = "📎" if self.ruta_archivo else ""
        revisado_str = "👁️" if self.revisado else ""
        comentario_str = f"({self.comentario})" if self.comentario else ""
        sub_str = {"Subsanable": "(S)", "No Subsanable": "(NS)"}.get(self.subsanable, "")
        return f"{estado} {revisado_str} {adjunto} [{self.codigo}] {self.nombre} {sub_str} {comentario_str}".strip()


@dataclass
class Empresa:
    nombre: str

    def to_dict(self) -> Dict[str, Any]:
        return {"nombre": self.nombre}

    def __str__(self) -> str:
        return self.nombre


@dataclass
class Licitacion:
    id: Optional[int] = None
    nombre_proceso: str = ""
    numero_proceso: str = ""
    institucion: str = ""

    empresas_nuestras: List[Empresa] = field(default_factory=list)
    estado: str = "Iniciada"
    fase_A_superada: bool = False
    fase_B_superada: bool = False
    adjudicada: bool = False
    adjudicada_a: str = ""
    motivo_descalificacion: str = ""
    docs_completos_manual: bool = False
    last_modified: Optional[str] = None
    fallas_fase_a: List[Dict[str, Any]] = field(default_factory=list)

    _parametros_evaluacion: Dict[str, Any] = field(default_factory=dict)

    fecha_creacion: datetime.date = field(default_factory=datetime.date.today)

    lotes: List[Lote] = field(default_factory=list)
    oferentes_participantes: List[Oferente] = field(default_factory=list)
    documentos_solicitados: List[Documento] = field(default_factory=list)

    cronograma: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.fecha_creacion, str):
            try:
                self.fecha_creacion = datetime.datetime.strptime(self.fecha_creacion, "%Y-%m-%d").date()
            except Exception:
                self.fecha_creacion = datetime.date.today()

    @property
    def parametros_evaluacion(self) -> Dict[str, Any]:
        return self._parametros_evaluacion or {}

    @parametros_evaluacion.setter
    def parametros_evaluacion(self, value: Any) -> None:
        self._parametros_evaluacion = as_dict(value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre_proceso": self.nombre_proceso,
            "numero_proceso": self.numero_proceso,
            "institucion": self.institucion,
            "empresas_nuestras": [e.to_dict() for e in self.empresas_nuestras],
            "estado": self.estado,
            "fase_A_superada": self.fase_A_superada,
            "fase_B_superada": self.fase_B_superada,
            "adjudicada": self.adjudicada,
            "adjudicada_a": self.adjudicada_a,
            "motivo_descalificacion": self.motivo_descalificacion,
            "docs_completos_manual": self.docs_completos_manual,
            "last_modified": self.last_modified,
            "fecha_creacion": str(self.fecha_creacion),
            "lotes": [l.to_dict() for l in self.lotes],
            "oferentes_participantes": [o.to_dict() for o in self.oferentes_participantes],
            "documentos_solicitados": [d.to_dict() for d in self.documentos_solicitados],
            "cronograma": self.cronograma,
            "fallas_fase_a": self.fallas_fase_a,
            "parametros_evaluacion": self._parametros_evaluacion,
        }

    def to_row(self) -> Dict[str, Any]:
        data = self.to_dict()
        data["parametros_evaluacion"] = json.dumps(self.parametros_evaluacion or {})
        data["cronograma"] = json.dumps(self.cronograma or {})
        data["empresas_nuestras"] = json.dumps([e.to_dict() for e in self.empresas_nuestras])
        data["lotes"] = json.dumps([l.to_dict() for l in self.lotes])
        data["oferentes_participantes"] = json.dumps([o.to_dict() for o in self.oferentes_participantes])
        data["documentos_solicitados"] = json.dumps([d.to_dict() for d in self.documentos_solicitados])
        return data

    def get_monto_base_total(self, solo_participados: bool = False) -> float:
        lotes = self.lotes
        if solo_participados:
            lotes = [l for l in lotes if l.participamos]
        return float(sum(float(l.monto_base or 0.0) for l in lotes))

    def get_oferta_total(self, solo_participados: bool = False) -> float:
        lotes = self.lotes
        if solo_participados:
            lotes = [l for l in lotes if l.participamos]
        return float(sum(float(l.monto_ofertado or 0.0) for l in lotes))

    def get_monto_base_personal_total(self, solo_participados: bool = False) -> float:
        lotes = self.lotes
        if solo_participados:
            lotes = [l for l in lotes if l.participamos]
        total = 0.0
        for l in lotes:
            personal = float(l.monto_base_personal or 0.0)
            if personal <= 0.0:
                personal = float(l.monto_base or 0.0)
            total += personal
        return total

    def get_diferencia_porcentual(self, solo_participados: bool = False, usar_base_personal: bool = True) -> float:
        lotes = self.lotes
        if solo_participados:
            lotes = [l for l in lotes if l.participamos or (float(l.monto_ofertado or 0) > 0)]
        base_total = 0.0
        oferta_total = 0.0
        for lote in lotes:
            oferta = float(lote.monto_ofertado or 0)
            if usar_base_personal:
                base = float(lote.monto_base_personal or 0.0) or float(lote.monto_base or 0.0)
            else:
                base = float(lote.monto_base or 0.0)
            base_total += base
            oferta_total += oferta
        if base_total == 0:
            return 0.0
        return ((oferta_total - base_total) / base_total) * 100.0

    def get_porcentaje_completado(self) -> float:
        total_docs = len(self.documentos_solicitados)
        if total_docs == 0:
            return 100.0 if self.docs_completos_manual else 0.0
        docs_completados = sum(1 for d in self.documentos_solicitados if d.presentado and not d.requiere_subsanacion)
        return (docs_completados / total_docs) * 100.0

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "numero_proceso": self.numero_proceso,
            "nombre_proceso": self.nombre_proceso,
            "institucion": self.institucion,
            "empresa_nuestra": ", ".join(str(e) for e in self.empresas_nuestras),
            "estado": self.estado,
            "monto_ofertado_total": self.get_oferta_total(),
            "cantidad_lotes": len(self.lotes),
            "cantidad_documentos": len(self.documentos_solicitados),
        }
    
    def get_matriz_ofertas(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
            """
            Genera una matriz (diccionario anidado) con las ofertas habilitadas
            de los competidores para cada lote.

            Formato: {
                'numero_lote_str': {
                    'nombre_competidor': {'monto': float, 'paso_fase_A': True, ...},
                    ...
                },
                ...
            }
            Solo incluye ofertas de competidores con paso_fase_A = True y monto > 0.
            NO incluye nuestra propia oferta aquí.
            """
            matriz: Dict[str, Dict[str, Dict[str, Any]]] = {}

            # Asegurarse de que oferentes_participantes es una lista
            oferentes = getattr(self, "oferentes_participantes", [])
            if not isinstance(oferentes, list):
                oferentes = []

            for oferente in oferentes:
                # Asegurarse de que oferente es un objeto con atributos
                # o manejar si fuera un dict (aunque debería ser objeto)
                nombre_oferente = getattr(oferente, "nombre", None)
                if not nombre_oferente:
                    continue # Saltar si no se puede obtener el nombre

                ofertas_por_lote = getattr(oferente, "ofertas_por_lote", [])
                if not isinstance(ofertas_por_lote, list):
                    ofertas_por_lote = [] # Asegurar que sea iterable

                for oferta_dict in ofertas_por_lote:
                    # Verificar que la oferta sea un diccionario
                    if not isinstance(oferta_dict, dict):
                        continue

                    paso_fase_a = oferta_dict.get('paso_fase_A', False)
                    monto = 0.0
                    try:
                        # Intentar convertir monto a float, manejar None o errores
                        monto_val = oferta_dict.get('monto')
                        if monto_val is not None:
                            monto = float(monto_val)
                    except (ValueError, TypeError):
                        monto = 0.0 # Considerar inválido si no es número

                    lote_num_val = oferta_dict.get('lote_numero')
                    lote_num_str = str(lote_num_val).strip() if lote_num_val is not None else None

                    # Incluir solo si pasó Fase A, tiene número de lote y monto válido
                    if paso_fase_a and lote_num_str and monto > 0:
                        # Crear entrada para el lote si no existe
                        if lote_num_str not in matriz:
                            matriz[lote_num_str] = {}
                        # Añadir la oferta del competidor (copia del dict)
                        matriz[lote_num_str][nombre_oferente] = oferta_dict.copy()

            return matriz
    

    def calcular_mejor_paquete_individual(self) -> Dict[str, Any]:
        """
        Calcula el paquete hipotético seleccionando la oferta más baja
        (habilitada) para cada lote individualmente, sin importar el oferente.

        Returns:
            Dict: {'monto_total': float, 'detalles_por_lote': Dict[str, Dict]}
                  Donde detalles_por_lote tiene {lote_num: {'oferente': str, 'monto': float}}
        """
        matriz = self.get_matriz_ofertas() # Solo competidores habilitados
        monto_total = 0.0
        detalles: Dict[str, Dict] = {}

        for lote in getattr(self, "lotes", []):
            lote_num_str = str(lote.numero)
            ofertas_lote = matriz.get(lote_num_str, {})

            # Considerar nuestra oferta si participamos y estamos habilitados
            mejor_oferta_lote = {'oferente': None, 'monto': float('inf')}
            if getattr(lote, 'participamos', False) and \
               getattr(lote, 'fase_A_superada', False) and \
               float(getattr(lote, 'monto_ofertado', 0) or 0) > 0:
                monto_nuestro = float(lote.monto_ofertado)
                if monto_nuestro < mejor_oferta_lote['monto']:
                     mejor_oferta_lote = {
                         'oferente': f"➡️ {lote.empresa_nuestra or 'Nuestra Oferta'}",
                         'monto': monto_nuestro
                     }

            # Comparar con competidores
            for oferente, data in ofertas_lote.items():
                monto_comp = data.get('monto', float('inf'))
                if isinstance(monto_comp, (int, float)) and monto_comp > 0:
                    if monto_comp < mejor_oferta_lote['monto']:
                        mejor_oferta_lote = {'oferente': oferente, 'monto': monto_comp}

            # Si se encontró una mejor oferta para este lote
            if mejor_oferta_lote['oferente'] is not None:
                monto_total += mejor_oferta_lote['monto']
                detalles[lote_num_str] = mejor_oferta_lote

        return {'monto_total': monto_total, 'detalles_por_lote': detalles}

    def calcular_mejor_paquete_por_oferente(self) -> Optional[Dict[str, Any]]:
        """
        Calcula el monto total que ofertó cada participante habilitado
        por TODOS los lotes y devuelve el paquete completo del oferente
        con el monto total más bajo.

        Returns:
            Optional[Dict]: {'oferente': str, 'monto_total': float, 'lotes_ofertados': int}
                            o None si ningún oferente ofertó por todos los lotes.
        """
        matriz = self.get_matriz_ofertas() # Solo competidores habilitados
        num_total_lotes = len(getattr(self, "lotes", []))
        if num_total_lotes == 0:
            return None

        paquetes_completos = []

        # Nuestra oferta (si participamos en todos los lotes habilitados)
        nuestra_empresa_unica = None
        monto_total_nuestro = 0.0
        lotes_ofertados_nuestro = 0
        todos_lotes_nuestros_ok = True
        nuestras_empresas = self._nuestras_empresas_de(self) # Reutilizar helper si existe, o implementarlo
        if len(nuestras_empresas) == 1:
            nuestra_empresa_unica = list(nuestras_empresas)[0]

        for lote in getattr(self, "lotes", []):
             if getattr(lote, 'participamos', False) and \
                getattr(lote, 'fase_A_superada', False) and \
                float(getattr(lote, 'monto_ofertado', 0) or 0) > 0:
                 monto_total_nuestro += float(lote.monto_ofertado)
                 lotes_ofertados_nuestro += 1
             elif getattr(lote, 'participamos', False): # Participamos pero no habilitados o sin monto
                 todos_lotes_nuestros_ok = False
                 # break # No podemos romper, necesitamos contar todos los lotes

        # Solo considerar nuestro paquete si ofertamos por todos y la empresa es única
        if todos_lotes_nuestros_ok and lotes_ofertados_nuestro == num_total_lotes and nuestra_empresa_unica:
             paquetes_completos.append({
                 'oferente': f"➡️ {nuestra_empresa_unica}",
                 'monto_total': monto_total_nuestro,
                 'lotes_ofertados': lotes_ofertados_nuestro
             })

        # Competidores
        oferentes = getattr(self, "oferentes_participantes", [])
        for oferente in oferentes:
            nombre_oferente = getattr(oferente, "nombre", None)
            if not nombre_oferente: continue

            monto_total_comp = 0.0
            lotes_ofertados_comp = 0
            ofertas_por_lote = getattr(oferente, "ofertas_por_lote", [])

            for oferta_dict in ofertas_por_lote:
                if isinstance(oferta_dict, dict) and \
                   oferta_dict.get('paso_fase_A', False) and \
                   float(oferta_dict.get('monto', 0) or 0) > 0:
                    monto_total_comp += float(oferta_dict['monto'])
                    lotes_ofertados_comp += 1

            # Solo considerar si ofertó por TODOS los lotes
            if lotes_ofertados_comp == num_total_lotes:
                paquetes_completos.append({
                    'oferente': nombre_oferente,
                    'monto_total': monto_total_comp,
                    'lotes_ofertados': lotes_ofertados_comp
                })

        if not paquetes_completos:
            return None

        # Devolver el paquete con el menor monto total
        mejor_paquete = min(paquetes_completos, key=lambda p: p['monto_total'])
        return mejor_paquete

    # Helper (si no lo tienes ya de antes)
    def _nuestras_empresas_de(self, lic) -> set:
        empresas = set()
        # Primero, de los lotes donde participamos
        for lote in getattr(lic, "lotes", []):
            if getattr(lote, "participamos", False):
                 nombre_empresa_lote = getattr(lote, "empresa_nuestra", None)
                 if nombre_empresa_lote and isinstance(nombre_empresa_lote, str) and nombre_empresa_lote.strip():
                     empresas.add(nombre_empresa_lote.strip())
        # Si no hay en lotes, de la lista general
        if not empresas:
            for item in getattr(lic, "empresas_nuestras", []):
                nombre = None
                if isinstance(item, str): nombre = item
                elif hasattr(item, 'nombre'): nombre = getattr(item, 'nombre', None) # Si es objeto Empresa
                if nombre and isinstance(nombre, str) and nombre.strip() and nombre.lower() != 'none':
                    empresas.add(nombre.strip())
        return empresas