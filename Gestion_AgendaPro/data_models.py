# Importation des classes de date et heure pour la validation
from datetime import datetime
# Importation des types optionnels et conteneurs pour les annotations de type
from typing import Optional, List, Dict
# Importation de la classe Enum pour créer des énumérations
from enum import Enum
# Importation des classes de base Pydantic pour la validation des données
from pydantic import BaseModel, validator

class AppointmentRecurrence(str, Enum):
    """Énumération des types de récurrence possibles pour un rendez-vous"""
    NONE = "none"  # Pas de récurrence
    DAILY = "daily"  # Récurrence quotidienne
    WEEKLY = "weekly"  # Récurrence hebdomadaire
    MONTHLY = "monthly"  # Récurrence mensuelle
    YEARLY = "yearly"  # Récurrence annuelle

class AppointmentBase(BaseModel):
    """Modèle de base pour les données d'un rendez-vous"""
    date: str  # Date du rendez-vous au format YYYY-MM-DD
    time: str  # Heure du rendez-vous au format HH:MM
    title: str  # Titre du rendez-vous
    description: Optional[str] = None  # Description optionnelle du rendez-vous
    category: str = "Autre"  # Catégorie du rendez-vous (défaut: Autre)
    reminder: int = 0  # Temps de rappel en minutes avant le rendez-vous (défaut: 0)
    recurrence: AppointmentRecurrence = AppointmentRecurrence.NONE  # Type de récurrence (défaut: aucune)
    recurrence_end: Optional[str] = None  # Date de fin de récurrence optionnelle

    @validator('date')
    def validate_date(cls, v):
        """Validateur pour vérifier le format de la date"""
        try:  # Tentative de parsing de la date
            datetime.strptime(v, "%Y-%m-%d")  # Parsing avec le format attendu
            return v  # Retour de la date si valide
        except ValueError:  # Si le parsing échoue
            raise ValueError("Invalid date format. Use YYYY-MM-DD")  # Levée d'une erreur

    @validator('time')
    def validate_time(cls, v):
        """Validateur pour vérifier le format de l'heure"""
        try:  # Tentative de parsing de l'heure
            datetime.strptime(v, "%H:%M")  # Parsing avec le format attendu
            return v  # Retour de l'heure si valide
        except ValueError:  # Si le parsing échoue
            raise ValueError("Invalid time format. Use HH:MM")  # Levée d'une erreur

    @validator('recurrence_end')
    def validate_recurrence_end(cls, v, values):
        """Validateur pour vérifier la date de fin de récurrence"""
        if v and 'date' in values:  # Si une date de fin est fournie et qu'une date de début existe
            try:  # Tentative de parsing des dates
                end_date = datetime.strptime(v, "%Y-%m-%d")  # Parsing de la date de fin
                start_date = datetime.strptime(values['date'], "%Y-%m-%d")  # Parsing de la date de début
                if end_date < start_date:  # Vérification que la fin est après le début
                    raise ValueError("Recurrence end date must be after start date")  # Erreur si invalide
                return v  # Retour de la date si valide
            except ValueError:  # Si le parsing échoue
                raise ValueError("Invalid recurrence end date format. Use YYYY-MM-DD")  # Levée d'une erreur
        return v  # Retour de la valeur si pas de validation nécessaire

class AppointmentCreate(AppointmentBase):
    """Modèle pour la création d'un nouveau rendez-vous (hérite de AppointmentBase)"""
    pass  # Aucun champ supplémentaire nécessaire

class AppointmentUpdate(BaseModel):
    """Modèle pour la mise à jour d'un rendez-vous existant"""
    title: Optional[str] = None  # Titre optionnel à modifier
    description: Optional[str] = None  # Description optionnelle à modifier
    category: Optional[str] = None  # Catégorie optionnelle à modifier
    reminder: Optional[int] = None  # Rappel optionnel à modifier
    recurrence: Optional[AppointmentRecurrence] = None  # Récurrence optionnelle à modifier
    recurrence_end: Optional[str] = None  # Date de fin de récurrence optionnelle à modifier

class Appointment(AppointmentBase):
    """Modèle complet d'un rendez-vous avec identifiants"""
    id: int  # Identifiant unique du rendez-vous
    user_id: int  # Identifiant de l'utilisateur propriétaire

    class Config:
        orm_mode = True  # Activation du mode ORM pour la compatibilité avec la base de données

class UserBase(BaseModel):
    """Modèle de base pour les données d'un utilisateur"""
    username: str  # Nom d'utilisateur unique
    email: str  # Adresse email unique

class UserCreate(UserBase):
    """Modèle pour la création d'un nouvel utilisateur"""
    password: str  # Mot de passe de l'utilisateur (sera haché)

class User(UserBase):
    """Modèle complet d'un utilisateur avec identifiant"""
    id: int  # Identifiant unique de l'utilisateur

    class Config:
        orm_mode = True  # Activation du mode ORM pour la compatibilité avec la base de données

class SharePermission(str, Enum):
    """Énumération des permissions de partage possibles"""
    READ = "read"  # Permission de lecture seule
    WRITE = "write"  # Permission de lecture et écriture

class ShareBase(BaseModel):
    """Modèle de base pour le partage d'un rendez-vous"""
    appointment_id: int  # Identifiant du rendez-vous partagé
    user_id: int  # Identifiant de l'utilisateur avec qui le rendez-vous est partagé
    permissions: SharePermission  # Niveau de permission accordé

class ShareCreate(ShareBase):
    """Modèle pour la création d'un nouveau partage (hérite de ShareBase)"""
    pass  # Aucun champ supplémentaire nécessaire

class Share(ShareBase):
    """Modèle complet d'un partage avec identifiant"""
    id: int  # Identifiant unique du partage

    class Config:
        orm_mode = True  # Activation du mode ORM pour la compatibilité avec la base de données

class Token(BaseModel):
    """Modèle pour un token d'authentification JWT"""
    access_token: str  # Le token d'accès JWT
    token_type: str  # Type de token (généralement "bearer")

class TokenData(BaseModel):
    """Modèle pour les données extraites d'un token JWT"""
    username: Optional[str] = None  # Nom d'utilisateur extrait du token

class StatsCategories(BaseModel):
    """Modèle pour les statistiques par catégorie"""
    categories: Dict[str, int]  # Dictionnaire des catégories avec leur count
    
class StatsMonthly(BaseModel):
    """Modèle pour les statistiques mensuelles"""
    monthly: Dict[str, int]  # Dictionnaire des mois avec leur count
    
class StatsShared(BaseModel):
    """Modèle pour les statistiques de partage"""
    received: int  # Nombre de rendez-vous reçus en partage
    given: int  # Nombre de rendez-vous donnés en partage

class StatsResponse(BaseModel):
    """Modèle de réponse regroupant toutes les statistiques"""
    categories: StatsCategories  # Statistiques par catégorie
    monthly: StatsMonthly  # Statistiques mensuelles
    shared: StatsShared  # Statistiques de partage