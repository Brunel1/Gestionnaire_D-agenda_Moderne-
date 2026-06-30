# Importation de la bibliothèque tkinter pour l'interface graphique
import tkinter as tk
# Importation des widgets ttk et des boîtes de dialogue depuis tkinter
from tkinter import ttk, messagebox
# Importation de la fonction d'initialisation de la base de données
from database_manager import init_db
# Importation de la classe principale de l'interface utilisateur
from gui_interface import AgendaApp
# Importation de la bibliothèque sv_ttk pour le thème moderne
import sv_ttk
# Importation du module de logging pour la journalisation
import logging
# Importation du gestionnaire d'authentification
from auth_manager import AuthManager

def configure_logging():
    """Configure le système de journalisation de l'application"""
    # Configuration basique du logging avec niveau INFO
    logging.basicConfig(
        level=logging.INFO,  # Niveau de journalisation : INFO
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format des messages
        filename='agenda.log'  # Fichier de sortie des logs
    )

class LoginWindow:
    """Classe représentant la fenêtre de connexion des utilisateurs"""
    
    def __init__(self, root):
        """Initialise la fenêtre de connexion avec tous ses composants"""
        self.root = root  # Stockage de la référence à la fenêtre racine
        self.root.title("Agenda ModernePro - Connexion")  # Définition du titre de la fenêtre
        self.root.geometry("400x300")  # Définition des dimensions de la fenêtre
        
        # Application du thème moderne clair
        sv_ttk.set_theme("light")
        
        # Création du cadre principal avec un padding de 20 pixels
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)  # Remplissage horizontal et vertical
        
        # Création du titre de la fenêtre
        ttk.Label(main_frame, text="Connexion", font=('Arial', 16)).pack(pady=10)
        
        # Création du cadre du formulaire de connexion
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)  # Remplissage horizontal uniquement
        
        # Label pour le champ nom d'utilisateur
        ttk.Label(form_frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(form_frame)  # Champ de saisie du nom d'utilisateur
        self.username_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        # Label pour le champ mot de passe
        ttk.Label(form_frame, text="Mot de passe:").grid(row=1, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(form_frame, show="*")  # Champ de saisie du mot de passe (masqué)
        self.password_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        # Création du cadre des boutons d'action
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        # Bouton de connexion
        ttk.Button(
            btn_frame, 
            text="Connexion", 
            command=self.login  # Appel de la méthode de connexion
        ).pack(side=tk.LEFT, padx=5)
        
        # Bouton d'inscription
        ttk.Button(
            btn_frame, 
            text="Inscription", 
            command=self.show_register  # Appel de la méthode d'affichage d'inscription
        ).pack(side=tk.LEFT)
        
        # Bouton de fermeture de l'application
        ttk.Button(
            btn_frame, 
            text="Quitter", 
            command=self.root.quit  # Fermeture de l'application
        ).pack(side=tk.RIGHT)
    
    def login(self):
        """Tente d'authentifier l'utilisateur avec les identifiants saisis"""
        username = self.username_entry.get()  # Récupération du nom d'utilisateur saisi
        password = self.password_entry.get()  # Récupération du mot de passe saisi
        
        # Vérification que tous les champs sont remplis
        if not username or not password:
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs")  # Affichage d'un avertissement
            return  # Arrêt de la méthode
        
        # Authentification de l'utilisateur via le gestionnaire d'authentification
        user = AuthManager.authenticate_user(username, password)
        if user:  # Si l'authentification réussit
            self.root.destroy()  # Fermeture de la fenêtre de connexion
            start_main_app(user["id"])  # Lancement de l'application principale avec l'ID utilisateur
        else:  # Si l'authentification échoue
            messagebox.showerror("Erreur", "Nom d'utilisateur ou mot de passe incorrect")  # Affichage d'une erreur
    
    def show_register(self):
        """Affiche la fenêtre d'inscription pour un nouvel utilisateur"""
        RegisterWindow(tk.Toplevel(self.root))  # Création d'une fenêtre secondaire pour l'inscription

class RegisterWindow:
    """Classe représentant la fenêtre d'inscription des nouveaux utilisateurs"""
    
    def __init__(self, root):
        """Initialise la fenêtre d'inscription avec tous ses composants"""
        self.root = root  # Stockage de la référence à la fenêtre racine
        self.root.title("Agenda ModernePro - Inscription")  # Définition du titre de la fenêtre
        self.root.geometry("400x350")  # Définition des dimensions de la fenêtre
        
        # Application du thème moderne clair
        sv_ttk.set_theme("light")
        
        # Création du cadre principal avec un padding de 20 pixels
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)  # Remplissage horizontal et vertical
        
        # Création du titre de la fenêtre
        ttk.Label(main_frame, text="Inscription", font=('Arial', 16)).pack(pady=10)
        
        # Création du cadre du formulaire d'inscription
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)  # Remplissage horizontal uniquement
        
        # Label pour le champ nom d'utilisateur
        ttk.Label(form_frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(form_frame)  # Champ de saisie du nom d'utilisateur
        self.username_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        # Label pour le champ email
        ttk.Label(form_frame, text="Email:").grid(row=1, column=0, sticky="w", pady=5)
        self.email_entry = ttk.Entry(form_frame)  # Champ de saisie de l'email
        self.email_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        # Label pour le champ mot de passe
        ttk.Label(form_frame, text="Mot de passe:").grid(row=2, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(form_frame, show="*")  # Champ de saisie du mot de passe (masqué)
        self.password_entry.grid(row=2, column=1, sticky="ew", pady=5)
        
        # Label pour le champ de confirmation du mot de passe
        ttk.Label(form_frame, text="Confirmer mot de passe:").grid(row=3, column=0, sticky="w", pady=5)
        self.confirm_entry = ttk.Entry(form_frame, show="*")  # Champ de confirmation du mot de passe (masqué)
        self.confirm_entry.grid(row=3, column=1, sticky="ew", pady=5)
        
        # Création du cadre des boutons d'action
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        # Bouton d'inscription
        ttk.Button(
            btn_frame, 
            text="S'inscrire", 
            command=self.register  # Appel de la méthode d'inscription
        ).pack(side=tk.LEFT, padx=5)
        
        # Bouton d'annulation
        ttk.Button(
            btn_frame, 
            text="Annuler", 
            command=self.root.destroy  # Fermeture de la fenêtre
        ).pack(side=tk.LEFT)
    
    def register(self):
        """Tente d'enregistrer un nouvel utilisateur dans la base de données"""
        username = self.username_entry.get()  # Récupération du nom d'utilisateur saisi
        email = self.email_entry.get()  # Récupération de l'email saisi
        password = self.password_entry.get()  # Récupération du mot de passe saisi
        confirm = self.confirm_entry.get()  # Récupération de la confirmation du mot de passe
        
        # Vérification que tous les champs sont remplis
        if not all([username, email, password, confirm]):
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs")  # Affichage d'un avertissement
            return  # Arrêt de la méthode
        
        # Vérification que les mots de passe correspondent
        if password != confirm:
            messagebox.showwarning("Erreur", "Les mots de passe ne correspondent pas")  # Affichage d'un avertissement
            return  # Arrêt de la méthode
        
        # Vérification que le mot de passe fait au moins 8 caractères
        if len(password) < 8:
            messagebox.showwarning("Erreur", "Le mot de passe doit faire au moins 8 caractères")  # Affichage d'un avertissement
            return  # Arrêt de la méthode
        
        # Création de l'utilisateur via le gestionnaire d'authentification
        user_id = AuthManager.create_user(username, password, email)
        if user_id:  # Si la création réussit
            messagebox.showinfo("Succès", "Inscription réussie! Vous pouvez maintenant vous connecter.")  # Affichage d'un succès
            self.root.destroy()  # Fermeture de la fenêtre d'inscription
        else:  # Si la création échoue
            messagebox.showerror("Erreur", "Ce nom d'utilisateur ou email est déjà utilisé")  # Affichage d'une erreur

def start_main_app(user_id: int):
    """Démarre l'application principale avec l'interface utilisateur"""
    root = tk.Tk()  # Création de la fenêtre principale
    root.title("Agenda ModernePr By HerveBrunel")  # Définition du titre de l'application
    root.geometry("1200x800")  # Définition des dimensions de la fenêtre
    
    sv_ttk.set_theme("light")  # Application du thème moderne clair
    
    try:  # Bloc de try pour gérer les erreurs potentielles
        app = AgendaApp(root, user_id)  # Création de l'instance de l'application principale
        root.mainloop()  # Lancement de la boucle principale de l'interface
    except Exception as e:  # Capture des exceptions
        logging.error(f"Application error: {e}")  # Journalisation de l'erreur
        raise  # Relancement de l'exception pour débogage

if __name__ == "__main__":
    configure_logging()  # Configuration du système de journalisation
    init_db()  # Initialisation de la base de données
    
    # Démarrage de l'application avec la fenêtre de connexion
    login_root = tk.Tk()  # Création de la fenêtre racine pour la connexion
    LoginWindow(login_root)  # Création de la fenêtre de connexion
    login_root.mainloop()  # Lancement de la boucle principale de la fenêtre de connexion