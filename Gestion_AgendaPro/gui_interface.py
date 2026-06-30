import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import sv_ttk
import webbrowser

from database_manager import (
    get_appointments_by_day, get_appointments_by_period,
    add_appointment, update_appointment, delete_appointment,
    get_appointment_by_id, search_appointments,
    export_to_json, import_from_json, export_to_ical,
    get_statistics
)
from notification_service import NotificationManager
from sharing_manager import SharingDialog
from cloud_sync_service import CloudSyncManager
from statistics_view import StatsView
from data_models import AppointmentRecurrence

class AgendaApp:
    """Application principale de gestion d'agenda"""
    
    def __init__(self, root, user_id: int):
        self.root = root
        self.user_id = user_id
        self.current_date = datetime.now()
        self.view_mode = "month"  # month, week, day
        self.search_var = tk.StringVar()
        
        # Configuration UI
        self.categories = ["Travail", "Personnel", "Santé", "Loisirs", "Réunion", "Autre"]
        self.category_colors = {
            "Travail": "#FFCCBC",
            "Personnel": "#C5E1A5",
            "Santé": "#81D4FA",
            "Loisirs": "#FFF59D",
            "Réunion": "#E1BEE7",
            "Autre": "#CFD8DC"
        }
        
        # Services
        self.notif_manager = NotificationManager(self.user_id)
        self.cloud_sync = CloudSyncManager(self.user_id)
        
        # Initialisation
        self.setup_ui()
        self.notif_manager.start()
        self.cloud_sync.start()
        
        # Gestion de la fermeture
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
    
    def setup_ui(self):
        """Configure toute l'interface utilisateur"""
        self.create_menu()
        self.create_toolbar()
        self.create_main_frame()
        self.create_status_bar()
        self.update_display()
    
    def create_menu(self):
        """Crée la barre de menu principale"""
        menubar = tk.Menu(self.root)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exporter JSON", command=self.export_json)
        file_menu.add_command(label="Importer JSON", command=self.import_json)
        file_menu.add_command(label="Exporter iCal", command=self.export_ical)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.on_quit)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        
        # Menu Édition
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Nouveau RDV", command=self.new_appointment)
        edit_menu.add_command(label="Modifier RDV", command=self.edit_selected)
        edit_menu.add_command(label="Supprimer RDV", command=self.delete_selected)
        menubar.add_cascade(label="Édition", menu=edit_menu)
        
        # Menu Affichage
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Vue Mois", command=lambda: self.set_view("month"))
        view_menu.add_command(label="Vue Semaine", command=lambda: self.set_view("week"))
        view_menu.add_command(label="Vue Jour", command=lambda: self.set_view("day"))
        view_menu.add_separator()
        view_menu.add_command(label="Statistiques", command=self.show_stats)
        menubar.add_cascade(label="Affichage", menu=view_menu)
        
        # Menu Partage
        share_menu = tk.Menu(menubar, tearoff=0)
        share_menu.add_command(label="Partager un RDV", command=self.share_appointment)
        share_menu.add_command(label="RDV partagés", command=self.show_shared)
        menubar.add_cascade(label="Partage", menu=share_menu)
        
        self.root.config(menu=menubar)
    
    def create_toolbar(self):
        """Crée la barre d'outils avec les actions principales"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation
        ttk.Button(toolbar, text="◀", command=self.previous_period, width=3).pack(side=tk.LEFT)
        self.date_label = ttk.Label(toolbar, text="", font=('Arial', 14, 'bold'))
        self.date_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(toolbar, text="▶", command=self.next_period, width=3).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Aujourd'hui", command=self.go_today).pack(side=tk.LEFT, padx=10)
        
        # Sélecteur de vue
        view_frame = ttk.Frame(toolbar)
        view_frame.pack(side=tk.LEFT, padx=20)
        ttk.Button(view_frame, text="Mois", command=lambda: self.set_view("month")).pack(side=tk.LEFT)
        ttk.Button(view_frame, text="Semaine", command=lambda: self.set_view("week")).pack(side=tk.LEFT)
        ttk.Button(view_frame, text="Jour", command=lambda: self.set_view("day")).pack(side=tk.LEFT)
        
        # Outils
        tools_frame = ttk.Frame(toolbar)
        tools_frame.pack(side=tk.RIGHT)
        
        ttk.Button(tools_frame, text="+ RDV", command=self.new_appointment).pack(side=tk.LEFT, padx=5)
        
        # Recherche
        search_frame = ttk.Frame(tools_frame)
        search_frame.pack(side=tk.LEFT, padx=10)
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT)
        search_entry.bind("<Return>", self.do_search)
        
        ttk.Button(search_frame, text="🔍", command=self.do_search, width=3).pack(side=tk.LEFT)
    
    def create_main_frame(self):
        """Crée le cadre principal qui contiendra l'affichage des RDV"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_status_bar(self):
        """Crée la barre de statut en bas de la fenêtre"""
        self.status_bar = ttk.Frame(self.root, height=25)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.sync_status = ttk.Label(self.status_bar, text="Sync: Disconnected")
        self.sync_status.pack(side=tk.LEFT, padx=5)
        
        self.status_message = ttk.Label(self.status_bar, text="Prêt")
        self.status_message.pack(side=tk.RIGHT, padx=5)
    
    def update_display(self):
        """Met à jour l'affichage en fonction du mode de vue actuel"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        if self.view_mode == "month":
            self.show_month_view()
        elif self.view_mode == "week":
            self.show_week_view()
        else:
            self.show_day_view()
    
    def show_month_view(self):
        """Affiche la vue mensuelle"""
        first_day = self.current_date.replace(day=1)
        last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        self._show_period_view(
            title=first_day.strftime("%B %Y"),
            start_date=first_day.strftime("%Y-%m-%d"),
            end_date=last_day.strftime("%Y-%m-%d")
        )
    
    def show_week_view(self):
        """Affiche la vue hebdomadaire"""
        start_date = self.current_date - timedelta(days=self.current_date.weekday())
        end_date = start_date + timedelta(days=6)
        
        self._show_period_view(
            title=f"Semaine du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
    
    def show_day_view(self):
        """Affiche la vue journalière"""
        date_str = self.current_date.strftime("%Y-%m-%d")
        self._show_period_view(
            title=self.current_date.strftime("%A %d %B %Y"),
            start_date=date_str,
            end_date=date_str
        )
    
    def _show_period_view(self, title: str, start_date: str, end_date: str):
        """Affiche les RDV pour une période donnée"""
        self.date_label.config(text=title)
        
        appointments = get_appointments_by_period(
            start_date, end_date, self.user_id
        )
        
        if not appointments:
            ttk.Label(
                self.main_frame, 
                text="Aucun rendez-vous pour cette période",
                font=('Arial', 12)
            ).pack(expand=True)
            return
        
        # Création du Treeview
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Date", "Heure", "Titre", "Catégorie", "Description")
        tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings",
            selectmode="browse"
        )
        
        # Configuration des colonnes
        tree.column("Date", width=100, anchor="center")
        tree.column("Heure", width=80, anchor="center")
        tree.column("Titre", width=150)
        tree.column("Catégorie", width=100, anchor="center")
        tree.column("Description", width=250)
        
        for col in columns:
            tree.heading(col, text=col)
        
        # Ajout des données
        for appt in appointments:
            tree.insert("", "end", 
                values=(
                    appt["date"],
                    appt["heure"],
                    appt["titre"],
                    appt["categorie"],
                    appt.get("description", "")[:50] + "..." if appt.get("description") else ""
                ),
                tags=(appt["categorie"],)
            )
        
        # Configuration des couleurs par catégorie
        for cat in self.categories:
            tree.tag_configure(cat, background=self.category_colors.get(cat, "#FFFFFF"))
        
        # Barre de défilement
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        
        # Événements
        tree.bind("<Double-1>", self.on_appointment_double_click)
        self.current_tree = tree
    
    def on_appointment_double_click(self, event):
        """Gère le double-clic sur un rendez-vous"""
        item = self.current_tree.selection()[0]
        values = self.current_tree.item(item, "values")
        
        appointments = get_appointments_by_day(values[0], self.user_id)
        for appt in appointments:
            if appt["heure"] == values[1] and appt["titre"] == values[2]:
                self.open_appointment_window(appt["id"])
                break
    
    # Navigation
    def previous_period(self):
        """Passe à la période précédente"""
        if self.view_mode == "month":
            self.current_date = self.current_date.replace(day=1) - timedelta(days=1)
        elif self.view_mode == "week":
            self.current_date -= timedelta(weeks=1)
        else:
            self.current_date -= timedelta(days=1)
        self.update_display()
    
    def next_period(self):
        """Passe à la période suivante"""
        if self.view_mode == "month":
            self.current_date = (self.current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        elif self.view_mode == "week":
            self.current_date += timedelta(weeks=1)
        else:
            self.current_date += timedelta(days=1)
        self.update_display()
    
    def go_today(self):
        """Retourne à la date actuelle"""
        self.current_date = datetime.now()
        self.update_display()
    
    def set_view(self, mode: str):
        """Change le mode d'affichage"""
        self.view_mode = mode
        self.update_display()
    
    # Gestion des rendez-vous
    def new_appointment(self):
        """Ouvre la fenêtre de création d'un nouveau RDV"""
        date = self.current_date.strftime("%Y-%m-%d")
        self.open_appointment_window(None, date)
    
    def edit_selected(self):
        """Modifie le rendez-vous sélectionné"""
        if hasattr(self, 'current_tree'):
            item = self.current_tree.selection()
            if item:
                values = self.current_tree.item(item, "values")
                appointments = get_appointments_by_day(values[0], self.user_id)
                for appt in appointments:
                    if appt["heure"] == values[1] and appt["titre"] == values[2]:
                        self.open_appointment_window(appt["id"])
                        return
        messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un rendez-vous à modifier")
    
    def delete_selected(self):
        """Supprime le rendez-vous sélectionné"""
        if hasattr(self, 'current_tree'):
            item = self.current_tree.selection()
            if item:
                values = self.current_tree.item(item, "values")
                if messagebox.askyesno(
                    "Confirmer", 
                    f"Supprimer le rendez-vous '{values[2]}' du {values[0]} à {values[1]} ?"
                ):
                    appointments = get_appointments_by_day(values[0], self.user_id)
                    for appt in appointments:
                        if appt["heure"] == values[1] and appt["titre"] == values[2]:
                            delete_appointment(appt["id"])
                            self.update_display()
                            return
        messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un rendez-vous à supprimer")
    
    def open_appointment_window(self, appt_id: Optional[int], date: Optional[str] = None):
        """Ouvre la fenêtre d'édition d'un rendez-vous"""
        window = tk.Toplevel(self.root)
        window.title("Nouveau Rendez-vous" if not appt_id else "Modifier Rendez-vous")
        window.geometry("650x400")
        
        # Variables
        recurrence_var = tk.StringVar(value="none")
        recurrence_end_var = tk.StringVar()
        
        # Récupération des données existantes
        if appt_id:
            appointment = get_appointment_by_id(appt_id)
            if not appointment:
                messagebox.showerror("Erreur", "Rendez-vous introuvable")
                window.destroy()
                return
            date = appointment["date"]
        
        # Cadre principal
        main_frame = ttk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Formulaire
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=5)
        
        # Champs
        ttk.Label(form_frame, text="Date:").grid(row=0, column=0, sticky="w", pady=5)
        date_entry = ttk.Entry(form_frame)
        date_entry.insert(0, date)
        date_entry.grid(row=0, column=1, sticky="w")
        
        ttk.Label(form_frame, text="Heure:").grid(row=1, column=0, sticky="w", pady=5)
        time_entry = ttk.Entry(form_frame)
        if appt_id:
            time_entry.insert(0, appointment["heure"])
        time_entry.grid(row=1, column=1, sticky="w")
        
        ttk.Label(form_frame, text="Titre:").grid(row=2, column=0, sticky="w", pady=5)
        title_entry = ttk.Entry(form_frame)
        if appt_id:
            title_entry.insert(0, appointment["titre"])
        title_entry.grid(row=2, column=1, sticky="w")
        
        ttk.Label(form_frame, text="Description:").grid(row=3, column=0, sticky="nw", pady=5)
        desc_entry = tk.Text(form_frame, width=30, height=5)
        if appt_id:
            desc_entry.insert("1.0", appointment.get("description", ""))
        desc_entry.grid(row=3, column=1, sticky="w")
        
        ttk.Label(form_frame, text="Catégorie:").grid(row=4, column=0, sticky="w", pady=5)
        category_combo = ttk.Combobox(
            form_frame, 
            values=self.categories, 
            state="readonly"
        )
        category_combo.grid(row=4, column=1, sticky="w")
        if appt_id:
            category_combo.set(appointment.get("categorie", "Autre"))
        
        ttk.Label(form_frame, text="Rappel (minutes):").grid(row=5, column=0, sticky="w", pady=5)
        reminder_combo = ttk.Combobox(
            form_frame, 
            values=[0, 5, 10, 15, 30, 60, 120],
            state="readonly",
            width=5
        )
        reminder_combo.grid(row=5, column=1, sticky="w")
        if appt_id:
            reminder_combo.set(appointment.get("rappel", 0))
        
        # Récurrence
        ttk.Label(form_frame, text="Récurrence:").grid(row=6, column=0, sticky="w", pady=5)
        recurrence_frame = ttk.Frame(form_frame)
        recurrence_frame.grid(row=6, column=1, sticky="ew")
        
        recurrences = [
            ("Aucune", "none"),
            ("Quotidienne", "daily"),
            ("Hebdomadaire", "weekly"),
            ("Mensuelle", "monthly"),
            ("Annuelle", "yearly")
        ]
        
        for i, (text, mode) in enumerate(recurrences):
            rb = ttk.Radiobutton(
                recurrence_frame,
                text=text,
                variable=recurrence_var,
                value=mode
            )
            rb.pack(side=tk.LEFT)
            if appt_id and appointment.get("recurrence") == mode:
                recurrence_var.set(mode)
        
        ttk.Label(form_frame, text="Fin de récurrence:").grid(row=7, column=0, sticky="w", pady=5)
        recurrence_end_entry = ttk.Entry(form_frame, textvariable=recurrence_end_var)
        recurrence_end_entry.grid(row=7, column=1, sticky="ew")
        if appt_id and appointment.get("recurrence_end"):
            recurrence_end_var.set(appointment["recurrence_end"])
        
        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            btn_frame,
            text="Enregistrer",
            command=lambda: self.save_appointment(
                date_entry.get(),
                time_entry.get(),
                title_entry.get(),
                desc_entry.get("1.0", tk.END).strip(),
                category_combo.get(),
                int(reminder_combo.get()),
                recurrence_var.get(),
                recurrence_end_var.get(),
                appt_id,
                window
            ),
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Annuler",
            command=window.destroy
        ).pack(side=tk.LEFT)
    
    def save_appointment(
        self,
        date: str,
        time: str,
        title: str,
        description: str,
        category: str,
        reminder: int,
        recurrence: str,
        recurrence_end: str,
        appt_id: Optional[int],
        window: tk.Toplevel
    ):
        """Enregistre un rendez-vous"""
        if not title.strip():
            messagebox.showwarning("Validation", "Le titre est obligatoire")
            return
        
        try:
            if appt_id:
                update_appointment(
                    appt_id,
                    title,
                    description,
                    category,
                    reminder,
                    recurrence if recurrence != "none" else None,
                    recurrence_end if recurrence != "none" else None
                )
            else:
                add_appointment(
                    self.user_id,
                    date,
                    time,
                    title,
                    description,
                    category,
                    reminder,
                    recurrence if recurrence != "none" else None,
                    recurrence_end if recurrence != "none" else None
                )
            
            window.destroy()
            self.update_display()
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")
    
    # Fonctionnalités de partage
    def share_appointment(self):
        """Ouvre la fenêtre de partage d'un rendez-vous"""
        if hasattr(self, 'current_tree'):
            item = self.current_tree.selection()
            if item:
                values = self.current_tree.item(item, "values")
                appointments = get_appointments_by_day(values[0], self.user_id)
                for appt in appointments:
                    if appt["heure"] == values[1] and appt["titre"] == values[2]:
                        SharingDialog(self.root, appt["id"], self.user_id)
                        return
        messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un rendez-vous à partager")
    
    def show_shared(self):
        """Affiche les rendez-vous partagés"""
        from database import get_shared_appointments
        
        shared = get_shared_appointments(self.user_id)
        if not shared:
            messagebox.showinfo("Rendez-vous partagés", "Aucun rendez-vous partagé avec vous")
            return
        
        # Création d'une fenêtre pour afficher les RDV partagés
        window = tk.Toplevel(self.root)
        window.title("Rendez-vous partagés")
        window.geometry("800x400")
        
        # Treeview
        tree_frame = ttk.Frame(window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Date", "Heure", "Titre", "Propriétaire", "Permissions")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100 if col != "Titre" else 150)
        
        for appt in shared:
            tree.insert("", "end", values=(
                appt["date"],
                appt["heure"],
                appt["titre"],
                appt["owner"],
                appt["permissions"]
            ))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
    
    # Recherche
    def do_search(self, event=None):
        """Effectue une recherche dans les rendez-vous"""
        search_text = self.search_var.get().strip()
        if not search_text:
            return
        
        results = search_appointments(search_text, self.user_id)
        self.show_search_results(results)
    
    def show_search_results(self, results: List[Dict]):
        """Affiche les résultats de recherche"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        if not results:
            ttk.Label(
                self.main_frame, 
                text="Aucun résultat trouvé",
                font=('Arial', 12)
            ).pack(expand=True)
            return
        
        # Treeview
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Date", "Heure", "Titre", "Catégorie", "Description")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100 if col != "Description" else 200)
        
        for appt in results:
            tree.insert("", "end", values=(
                appt["date"],
                appt["heure"],
                appt["titre"],
                appt["categorie"],
                appt.get("description", "")[:100] + "..." if appt.get("description") else ""
            ), tags=(appt["categorie"],))
        
        for cat in self.categories:
            tree.tag_configure(cat, background=self.category_colors.get(cat, "#FFFFFF"))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        
        tree.bind("<Double-1>", self.on_search_result_double_click)
        self.current_tree = tree
    
    def on_search_result_double_click(self, event):
        """Gère le double-clic sur un résultat de recherche"""
        item = self.current_tree.selection()[0]
        values = self.current_tree.item(item, "values")
        
        self.current_date = datetime.strptime(values[0], "%Y-%m-%d")
        self.set_view("day")
        self.root.after(100, lambda: self.highlight_appointment(values[1], values[2]))
    
    def highlight_appointment(self, time: str, title: str):
        """Met en évidence un rendez-vous spécifique"""
        if hasattr(self, 'current_tree'):
            for child in self.current_tree.get_children():
                values = self.current_tree.item(child, "values")
                if values[1] == time and values[2] == title:
                    self.current_tree.selection_set(child)
                    self.current_tree.focus(child)
                    break
    
    # Import/Export
    def export_json(self):
        """Exporte les données au format JSON"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("Fichiers JSON", "*.json")]
            )
            if filename:
                count = export_to_json(self.user_id, filename)
                messagebox.showinfo("Succès", f"{count} rendez-vous exportés!")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'export: {str(e)}")
            logging.error(f"Export error: {e}")
    
    def import_json(self):
        """Importe des données depuis un fichier JSON"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("Fichiers JSON", "*.json")]
            )
            if filename:
                count = import_from_json(self.user_id, filename)
                messagebox.showinfo("Succès", f"{count} rendez-vous importés!")
                self.update_display()
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'import: {str(e)}")
            logging.error(f"Import error: {e}")
    
    def export_ical(self):
        """Exporte les données au format iCalendar"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".ics",
                filetypes=[("Fichiers iCalendar", "*.ics")]
            )
            if filename:
                count = export_to_ical(self.user_id, filename)
                messagebox.showinfo("Succès", f"{count} rendez-vous exportés!")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'export: {str(e)}")
            logging.error(f"iCal export error: {e}")
    
    # Statistiques
    def show_stats(self):
        """Affiche les statistiques"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Statistiques")
        stats_window.geometry("800x600")
        
        stats_view = StatsView(stats_window, self.user_id)
        stats_view.frame.pack(fill=tk.BOTH, expand=True)
    
    # Gestion de la fermeture
    def on_quit(self):
        """Ferme proprement l'application"""
        self.notif_manager.stop()
        self.cloud_sync.stop()
        self.root.quit()