import sqlite3
import bcrypt
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from contextlib import contextmanager

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Contexte pour la gestion des connexions DB
@contextmanager
def db_connection():
    conn = sqlite3.connect("agenda.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Table utilisateurs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Table rendez-vous avec contraintes et index
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rendez_vous (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            heure TEXT NOT NULL,
            titre TEXT NOT NULL,
            description TEXT,
            categorie TEXT DEFAULT 'Autre',
            rappel INTEGER DEFAULT 0,
            recurrence TEXT,
            recurrence_end TEXT,
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
            CHECK (rappel >= 0)
        )
        """)
        
        # Index pour les recherches fréquentes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rdv_user ON rendez_vous(utilisateur_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rdv_date ON rendez_vous(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rdv_categorie ON rendez_vous(categorie)")
        
        # Table partage
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS partages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rdv_id INTEGER NOT NULL,
            utilisateur_id INTEGER NOT NULL,
            permissions TEXT NOT NULL,  -- 'read' ou 'write'
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rdv_id) REFERENCES rendez_vous(id),
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
            UNIQUE(rdv_id, utilisateur_id)
        )
        """)
        
        conn.commit()

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(stored_hash: str, password: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

def create_user(username: str, password: str, email: str) -> int:
    """Crée un nouvel utilisateur"""
    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO utilisateurs (username, password_hash, email) VALUES (?, ?, ?)",
                (username, hash_password(password), email)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Username or email already exists")

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authentifie un utilisateur"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash FROM utilisateurs WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if user and verify_password(user['password_hash'], password):
            return dict(user)
        return None

# Fonctions de validation
def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def check_schedule_conflict(date: str, time: str, rdv_id: int = None, user_id: int = None) -> bool:
    """Vérifie s'il y a un conflit d'horaire"""
    with db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT id FROM rendez_vous 
            WHERE date = ? AND heure = ? AND utilisateur_id = ?
        """
        params = [date, time, user_id]
        
        if rdv_id:
            query += " AND id != ?"
            params.append(rdv_id)
        
        cursor.execute(query, params)
        return cursor.fetchone() is not None

# Fonctions CRUD pour les rendez-vous
def add_appointment(
    user_id: int,
    date: str,
    time: str,
    title: str,
    description: str = "",
    category: str = "Autre",
    reminder: int = 0,
    recurrence: str = None,
    recurrence_end: str = None
) -> int:
    """Ajoute un nouveau rendez-vous"""
    if not validate_date(date):
        raise ValueError("Format de date invalide (YYYY-MM-DD attendu)")
    if not validate_time(time):
        raise ValueError("Format d'heure invalide (HH:MM attendu)")
    if check_schedule_conflict(date, time, user_id=user_id):
        raise ValueError("Un rendez-vous existe déjà à cette heure")
    
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rendez_vous (
                utilisateur_id, date, heure, titre, description, 
                categorie, rappel, recurrence, recurrence_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, time, title, description, category, reminder, recurrence, recurrence_end))
        conn.commit()
        return cursor.lastrowid

def update_appointment(
    rdv_id: int,
    new_title: str,
    new_description: str,
    new_category: str,
    reminder: int,
    recurrence: str = None,
    recurrence_end: str = None
) -> bool:
    """Met à jour un rendez-vous existant"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE rendez_vous 
            SET titre = ?, description = ?, categorie = ?, 
                rappel = ?, recurrence = ?, recurrence_end = ?
            WHERE id = ?
        """, (new_title, new_description, new_category, reminder, recurrence, recurrence_end, rdv_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_appointment(rdv_id: int) -> bool:
    """Supprime un rendez-vous"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rendez_vous WHERE id = ?", (rdv_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_appointment_by_id(rdv_id: int) -> Optional[Dict]:
    """Récupère un rendez-vous par son ID"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rendez_vous WHERE id = ?", (rdv_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# Fonctions de recherche
def get_appointments_by_day(date: str, user_id: int) -> List[Dict]:
    """Récupère les rendez-vous d'un jour spécifique"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, heure, titre, description, categorie, rappel
            FROM rendez_vous 
            WHERE date = ? AND utilisateur_id = ?
            ORDER BY heure
        """, (date, user_id))
        return [dict(row) for row in cursor.fetchall()]

def get_appointments_by_period(
    start_date: str, 
    end_date: str, 
    user_id: int,
    sort_by: str = "date",
    order: str = "asc"
) -> List[Dict]:
    """Récupère les rendez-vous sur une période"""
    valid_sorts = ["date", "heure", "titre", "categorie"]
    if sort_by not in valid_sorts:
        sort_by = "date"
    
    order = "ASC" if order.lower() == "asc" else "DESC"
    
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, date, heure, titre, description, categorie, rappel
            FROM rendez_vous 
            WHERE date BETWEEN ? AND ? AND utilisateur_id = ?
            ORDER BY {sort_by} {order}, heure {order}
        """, (start_date, end_date, user_id))
        return [dict(row) for row in cursor.fetchall()]

def search_appointments(
    search_text: str,
    user_id: int,
    categories: List[str] = None,
    start_date: str = None,
    end_date: str = None
) -> List[Dict]:
    """Recherche avancée dans les rendez-vous"""
    query = """
        SELECT id, date, heure, titre, description, categorie
        FROM rendez_vous 
        WHERE (titre LIKE ? OR description LIKE ?) AND utilisateur_id = ?
    """
    params = [f"%{search_text}%", f"%{search_text}%", user_id]
    
    if categories:
        placeholders = ','.join(['?'] * len(categories))
        query += f" AND categorie IN ({placeholders})"
        params.extend(categories)
    
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

# Fonctions pour les notifications
def get_upcoming_appointments(user_id: int, limit: int = 10) -> List[Dict]:
    """Récupère les prochains rendez-vous"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, heure, titre, rappel
            FROM rendez_vous 
            WHERE utilisateur_id = ? AND datetime(date || ' ' || heure) > ?
            ORDER BY datetime(date || ' ' || heure)
            LIMIT ?
        """, (user_id, now, limit))
        return [dict(row) for row in cursor.fetchall()]

def get_appointments_to_notify(user_id: int) -> List[Dict]:
    """Récupère les rendez-vous nécessitant une notification"""
    now = datetime.now()
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, heure, titre, rappel
            FROM rendez_vous 
            WHERE utilisateur_id = ? 
              AND rappel > 0
              AND datetime(date || ' ' || heure) BETWEEN ? AND datetime(?, '+' || rappel || ' minutes')
        """, (user_id, now.strftime("%Y-%m-%d %H:%M"), now.strftime("%Y-%m-%d %H:%M")))
        return [dict(row) for row in cursor.fetchall()]

# Fonctions de partage
def share_appointment(rdv_id: int, owner_id: int, recipient_id: int, permissions: str = "read") -> bool:
    """Partage un rendez-vous avec un autre utilisateur"""
    if permissions not in ["read", "write"]:
        raise ValueError("Permissions must be 'read' or 'write'")
    
    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO partages (rdv_id, utilisateur_id, permissions)
                VALUES (?, ?, ?)
                ON CONFLICT(rdv_id, utilisateur_id) DO UPDATE SET permissions = ?
            """, (rdv_id, recipient_id, permissions, permissions))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValueError("Invalid appointment or user ID")

def get_shared_appointments(user_id: int) -> List[Dict]:
    """Récupère les rendez-vous partagés avec l'utilisateur"""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.date, r.heure, r.titre, r.description, r.categorie,
                   u.username as owner, p.permissions
            FROM rendez_vous r
            JOIN partages p ON r.id = p.rdv_id
            JOIN utilisateurs u ON r.utilisateur_id = u.id
            WHERE p.utilisateur_id = ?
            ORDER BY r.date, r.heure
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

# Fonctions d'import/export
def export_to_json(user_id: int, file_path: str) -> int:
    """Exporte les rendez-vous au format JSON"""
    appointments = get_appointments_by_period(
        "1900-01-01", "2100-12-31", user_id
    )
    
    data = {
        "version": 1,
        "user_id": user_id,
        "appointments": appointments,
        "exported_at": datetime.now().isoformat()
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return len(appointments)

def import_from_json(user_id: int, file_path: str) -> int:
    """Importe des rendez-vous depuis un fichier JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, dict) or "appointments" not in data:
        raise ValueError("Invalid JSON format")
    
    count = 0
    for appointment in data["appointments"]:
        try:
            add_appointment(
                user_id=user_id,
                date=appointment["date"],
                time=appointment["heure"],
                title=appointment["titre"],
                description=appointment.get("description", ""),
                category=appointment.get("categorie", "Autre"),
                reminder=appointment.get("rappel", 0),
                recurrence=appointment.get("recurrence"),
                recurrence_end=appointment.get("recurrence_end")
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to import appointment: {e}")
    
    return count

def export_to_ical(user_id: int, file_path: str) -> int:
    """Exporte les rendez-vous au format iCalendar"""
    from icalendar import Calendar, Event
    import pytz
    
    appointments = get_appointments_by_period(
        "1900-01-01", "2100-12-31", user_id
    )
    
    cal = Calendar()
    cal.add('prodid', '-//Agenda ModernePro//fr//')
    cal.add('version', '2.0')
    
    tz = pytz.timezone('Europe/Paris')
    
    for appt in appointments:
        event = Event()
        event.add('summary', appt['titre'])
        event.add('description', appt.get('description', ''))
        
        start_dt = datetime.strptime(f"{appt['date']} {appt['heure']}", "%Y-%m-%d %H:%M")
        start_dt = tz.localize(start_dt)
        event.add('dtstart', start_dt)
        event.add('dtend', start_dt + timedelta(hours=1))  # Durée par défaut 1h
        
        if appt.get('categorie'):
            event.add('categories', appt['categorie'])
        
        cal.add_component(event)
    
    with open(file_path, 'wb') as f:
        f.write(cal.to_ical())
    
    return len(appointments)

# Fonctions statistiques
def get_statistics(user_id: int) -> Dict[str, Any]:
    """Récupère des statistiques sur les rendez-vous"""
    stats = {
        'categories': {},
        'monthly': {},
        'shared': {
            'received': 0,
            'given': 0
        }
    }
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Stats par catégorie
        cursor.execute("""
            SELECT categorie, COUNT(*) as count 
            FROM rendez_vous 
            WHERE utilisateur_id = ?
            GROUP BY categorie
        """, (user_id,))
        stats['categories'] = dict(cursor.fetchall())
        
        # Stats mensuelles
        for month in range(1, 13):
            cursor.execute("""
                SELECT COUNT(*) 
                FROM rendez_vous
                WHERE utilisateur_id = ? AND strftime('%m', date) = ?
            """, (user_id, f"{month:02d}"))
            stats['monthly'][f"{month:02d}"] = cursor.fetchone()[0]
        
        # Stats partage
        cursor.execute("""
            SELECT COUNT(*) FROM partages
            WHERE utilisateur_id = ?
        """, (user_id,))
        stats['shared']['received'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM partages p
            JOIN rendez_vous r ON p.rdv_id = r.id
            WHERE r.utilisateur_id = ?
        """, (user_id,))
        stats['shared']['given'] = cursor.fetchone()[0]
    
    return stats