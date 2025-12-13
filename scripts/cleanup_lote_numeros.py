import sys
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

# ================= NORMALIZADOR =================

def normalize_lote_numero(raw):
    if not raw:
        return ""

    s = str(raw).strip().upper()
    m = re.search(r"(\d+)", s)
    if not m:
        return s

    return f"LOTE {int(m.group(1))}"

# ================= UI =================

def select_credentials():
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        "Credenciales Firebase",
        "Selecciona el archivo JSON de credenciales de Firebase"
    )

    path = filedialog.askopenfilename(
        title="Seleccionar credenciales Firebase",
        filetypes=[("JSON files", "*.json")]
    )

    if not path:
        messagebox.showerror("Cancelado", "No se seleccionaron credenciales.")
        sys.exit(1)

    return path

# ================= FIRESTORE =================

def init_firestore(credentials_path):
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()

# ================= MAIN =================

def main():
    cred_path = select_credentials()
    db = init_firestore(cred_path)

    collection = "licitaciones"
    docs = db.collection(collection).stream()

    total_docs = 0
    total_fixed = 0

    for doc in docs:
        data = doc.to_dict()
        lotes = data.get("lotes", [])
        changed = False

        for l in lotes:
            old = l.get("numero")
            new = normalize_lote_numero(old)
            if old != new:
                l["numero"] = new
                changed = True

        if changed:
            db.collection(collection).document(doc.id).set(data)
            total_fixed += 1

        total_docs += 1

    messagebox.showinfo(
        "Proceso terminado",
        f"Documentos revisados: {total_docs}\n"
        f"Documentos corregidos: {total_fixed}"
    )

if __name__ == "__main__":
    main()
