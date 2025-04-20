import sqlite3
import customtkinter as ctk
from tkinter import ttk, messagebox
import argparse
import sys

TABLE = "anmeldungen"

class DBViewerApp(ctk.CTk):
    def __init__(self, db_path):
        super().__init__()
        self.title("Datenbank-Viewer: Anmeldungen")
        self.geometry("1500x750")  # 25% breiter und höher
        self.resizable(True, True)
        try:
            self.conn = sqlite3.connect(db_path)
            self.cur = self.conn.cursor()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Öffnen der Datenbank: {e}")
            self.destroy()
            return
        self.status_var = None  # wird in create_widgets gesetzt
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        # Suchleiste & Status-Filter
        self.search_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Alle")
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=10, pady=(10, 0))
        search_frame.grid_columnconfigure(0, weight=1)
        search_frame.grid_columnconfigure(1, weight=0)

        # Linke Seite: Suchleiste
        left_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(left_frame, text="Suche:").pack(side="left")
        search_entry = ctk.CTkEntry(left_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda e: self.load_data())
        ctk.CTkButton(left_frame, text="Suchen", command=self.load_data).pack(side="left", padx=5)
        ctk.CTkButton(left_frame, text="Suchen zurücksetzen", command=self.reset_search).pack(side="left")

        # Rechte Seite: Statusfilter und Filter-Reset
        right_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(right_frame, text="Status:").pack(side="left")
        self.status_dropdown = ctk.CTkOptionMenu(right_frame, variable=self.status_var, values=["Alle"], command=lambda _: self.load_data())
        self.status_dropdown.pack(side="left", padx=5)
        ctk.CTkButton(right_frame, text="Filter zurücksetzen", command=self.reset_status_filter).pack(side="left", padx=5)
        self.update_status_options()

        # Tabelle (nur relevante Spalten anzeigen)
        self.display_columns = ["bestellnummer", "vorname", "name", "feieruhrzeit", "feiertag", "hint", "status", "created_at", "updated_at"]
        self.all_columns = ["id", "bestellnummer", "vorname", "name", "uid", "feieruhrzeit", "feiertag", "hint", "src_path", "work_path", "status", "created_at", "updated_at"]
        style = ttk.Style()
        style.configure("Treeview", rowheight=32)  # Zeilenhöhe erhöhen
        self.tree = ttk.Treeview(self, columns=self.display_columns, show="headings")
        for col in self.display_columns:
            anchor = "center"
            width = 120
            if col == "bestellnummer":
                width = 130  # 10px breiter
            if col == "name":
                anchor = "w"  # linksbündig
                width = 180  # 50% breiter
            elif col == "vorname":
                anchor = "e"  # rechtsbündig
            if col in ("created_at", "updated_at"):
                width = 180
            self.tree.heading(col, text=col.title(), command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # Scrollbars
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

    def load_data(self):
        search = self.search_var.get().strip()
        status = self.status_var.get()
        sql = f"SELECT * FROM {TABLE}"
        params = []
        where_clauses = []
        if search:
            where_clauses.append("(bestellnummer LIKE ? OR name LIKE ? OR vorname LIKE ? OR status LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like, like])
        if status and status != "Alle":
            where_clauses.append("status = ?")
            params.append(status)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY id DESC"
        self.cur.execute(sql, params)
        rows = self.cur.fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            # row ist in Reihenfolge self.all_columns
            # Korrekte Zuordnung: vorname = Spalte 2, name = Spalte 3 (Index 2 bzw. 3 in all_columns)
            display_row = []
            for col in self.display_columns:
                if col == "vorname":
                    display_row.append(row[3])
                elif col == "name":
                    display_row.append(row[2])
                else:
                    display_row.append(row[self.all_columns.index(col)])
            self.tree.insert("", "end", values=display_row, tags=(str(row[0]),))  # tag mit id für Detailansicht
        self.update_status_options()

    def reset_search(self):
        self.search_var.set("")
        self.load_data()

    def reset_status_filter(self):
        self.status_var.set("Alle")
        self.load_data()

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def update_status_options(self):
        # Hole alle unterschiedlichen Status aus der Datenbank
        try:
            self.cur.execute(f"SELECT DISTINCT status FROM {TABLE} ORDER BY status")
            status_list = [row[0] for row in self.cur.fetchall() if row[0]]
        except Exception:
            status_list = []
        values = ["Alle"] + status_list
        current = self.status_var.get() if self.status_var else "Alle"
        self.status_dropdown.configure(values=values)
        if current not in values:
            self.status_var.set("Alle")

    def on_row_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        values = self.tree.item(item[0], "values")
        EditDialog(self, values, self.conn, self.cur, self.load_data)

class EditDialog(ctk.CTkToplevel):
    def __init__(self, parent, values, conn, cur, reload_callback):
        super().__init__(parent)
        self.title(f"Eintrag bearbeiten: ID {values[0]}")
        self.geometry("600x600")
        self.conn = conn
        self.cur = cur
        self.reload_callback = reload_callback
        self.values = values
        self.vars = []
        labels = ["id", "bestellnummer", "name", "vorname", "uid", "feiertag", "feieruhrzeit", "hint", "src_path", "work_path", "status", "created_at", "updated_at"]
        for i, (label, value) in enumerate(zip(labels, values)):
            ctk.CTkLabel(self, text=label.title()).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            var = ctk.StringVar(value=value)
            entry = ctk.CTkEntry(self, textvariable=var, width=50)
            entry.grid(row=i, column=1, sticky="ew", padx=10, pady=5)
            if label in ("id", "created_at", "updated_at", "uid"):
                entry.configure(state="readonly")
            self.vars.append(var)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        ctk.CTkButton(btn_frame, text="Speichern", command=self.save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy).pack(side="left", padx=5)

    def save(self):
        labels = ["bestellnummer", "name", "vorname", "feiertag", "feieruhrzeit", "hint", "src_path", "work_path", "status"]
        values = [self.vars[i+1].get() for i in range(len(labels))]  # +1: id ist 0
        sql = f"UPDATE {TABLE} SET " + ", ".join(f"{col}=?" for col in labels) + " WHERE id=?"
        params = values + [self.vars[0].get()]
        try:
            self.cur.execute(sql, params)
            self.conn.commit()
            messagebox.showinfo("Gespeichert", "Eintrag erfolgreich aktualisiert.")
            self.reload_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Datenbank-Viewer für Anmeldungen")
    parser.add_argument("db_path", metavar="DB_PATH", type=str, help="Pfad zur SQLite-Datenbankdatei")
    args = parser.parse_args()

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = DBViewerApp(args.db_path)
    app.mainloop()
