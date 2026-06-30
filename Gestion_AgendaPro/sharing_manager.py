import tkinter as tk
from tkinter import ttk, messagebox
from database_manager import share_appointment
import re
import logging
from typing import Optional

class SharingDialog:
    """Dialogue pour partager un rendez-vous"""
    
    def __init__(self, parent, rdv_id: int, user_id: int):
        self.top = tk.Toplevel(parent)
        self.top.title("Partage de rendez-vous")
        self.rdv_id = rdv_id
        self.user_id = user_id
        
        self.create_widgets()
    
    def create_widgets(self):
        """Crée les éléments de l'interface"""
        main_frame = ttk.Frame(self.top, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Partager ce rendez-vous").grid(row=0, columnspan=2)
        
        # Email ou nom d'utilisateur
        ttk.Label(main_frame, text="Destinataire (email ou nom d'utilisateur):").grid(
            row=1, column=0, sticky="w", pady=10)
        self.recipient_entry = ttk.Entry(main_frame, width=30)
        self.recipient_entry.grid(row=1, column=1, sticky="ew", pady=10)
        
        # Permissions
        ttk.Label(main_frame, text="Permissions:").grid(row=2, column=0, sticky="w", pady=5)
        self.permission_var = tk.StringVar(value="read")
        
        permission_frame = ttk.Frame(main_frame)
        permission_frame.grid(row=2, column=1, sticky="ew")
        
        ttk.Radiobutton(
            permission_frame,
            text="Lecture seule",
            variable=self.permission_var,
            value="read"
        ).pack(side=tk.LEFT)
        
        ttk.Radiobutton(
            permission_frame,
            text="Lecture et écriture",
            variable=self.permission_var,
            value="write"
        ).pack(side=tk.LEFT)
        
        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, columnspan=2, pady=20)
        
        ttk.Button(
            btn_frame, 
            text="Partager", 
            command=self.validate_share,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame, 
            text="Annuler", 
            command=self.top.destroy
        ).pack(side=tk.LEFT)
    
    def validate_share(self):
        """Valide et effectue le partage"""
        recipient = self.recipient_entry.get().strip()
        permission = self.permission_var.get()
        
        if not recipient:
            messagebox.showwarning("Champ vide", "Veuillez entrer un email ou nom d'utilisateur")
            return
        
        try:
            # Dans une vraie application, on vérifierait d'abord que le destinataire existe
            # Pour cet exemple, on suppose que l'email/nom d'utilisateur est valide
            
            if share_appointment(
                self.rdv_id,
                self.user_id,
                recipient,  # Dans une vraie app, ce serait l'ID utilisateur
                permission
            ):
                messagebox.showinfo("Succès", "Rendez-vous partagé avec succès!")
                self.top.destroy()
            else:
                messagebox.showerror("Erreur", "Échec du partage. Vérifiez les informations.")
        
        except Exception as e:
            logging.error(f"Erreur lors du partage: {e}")
            messagebox.showerror("Erreur", "Une erreur technique est survenue")