import threading
import time
from datetime import datetime
import logging
import platform
from typing import Dict, List
from database_manager import db_connection

# Import spécifique au système d'exploitation
if platform.system() == "Windows":
    import winsound
else:
    import os  # Pour les systèmes Unix

from plyer import notification
from database_manager import get_appointments_to_notify

class NotificationManager:
    """Gère les notifications et rappels"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.active = True
        self.notification_thread = None
        self.notification_settings = {
            "sound": True,
            "popup": True,
            "duration": 30  # en secondes
        }
        self.logger = logging.getLogger(__name__)
        
    def start(self) -> None:
        """Démarre le service de notifications"""
        if not self.notification_thread or not self.notification_thread.is_alive():
            self.notification_thread = threading.Thread(
                target=self._notification_loop,
                daemon=True
            )
            self.notification_thread.start()
            self.logger.info("Notification service started")
    
    def stop(self) -> None:
        """Arrête le service de notifications"""
        self.active = False
        if self.notification_thread and self.notification_thread.is_alive():
            self.notification_thread.join()
        self.logger.info("Notification service stopped")
    
    def update_settings(self, settings: Dict) -> None:
        """Met à jour les paramètres de notification"""
        self.notification_settings.update(settings)
        self.logger.info("Notification settings updated")
    
    def _notification_loop(self) -> None:
        """Boucle principale de vérification des notifications"""
        while self.active:
            try:
                appointments = get_appointments_to_notify(self.user_id)
                for appt in appointments:
                    self._send_notification(appt)
                
                time.sleep(60)  # Vérifier toutes les minutes
            
            except Exception as e:
                self.logger.error(f"Notification error: {e}")
                time.sleep(300)  # En cas d'erreur, attendre 5 minutes
    
    def _send_notification(self, appointment: Dict) -> None:
        """Envoie une notification pour un rendez-vous"""
        title = f"Rappel: {appointment['titre']}"
        message = (
            f"Le {appointment['date']} à {appointment['heure']}\n"
            f"Catégorie: {appointment.get('categorie', 'Non spécifiée')}"
        )
        
        # Notification visuelle
        if self.notification_settings["popup"]:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=self.notification_settings["duration"]
                )
            except Exception as e:
                self.logger.error(f"Failed to show notification: {e}")
        
        # Son de notification
        if self.notification_settings["sound"]:
            self._play_notification_sound()
        
        self.logger.info(f"Notification sent for appointment {appointment['id']}")
    
    def _play_notification_sound(self) -> None:
        """Joue un son de notification selon le système d'exploitation"""
        try:
            if platform.system() == "Windows":
                winsound.Beep(1000, 500)  # Fréquence 1000Hz, durée 500ms
            else:
                # Pour Mac/Linux
                os.system('afplay /System/Library/Sounds/Ping.aiff' if platform.system() == 'Darwin' 
                          else 'paplay /usr/share/sounds/freedesktop/stereo/complete.oga')
        except Exception as e:
            self.logger.error(f"Failed to play sound: {e}")
    
    def check_immediate_notifications(self) -> List[Dict]:
        """Vérifie et retourne les notifications à afficher immédiatement"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        appointments = []
        
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, date, heure, titre, description, categorie
                FROM rendez_vous 
                WHERE utilisateur_id = ? AND datetime(date || ' ' || heure) BETWEEN ? AND datetime(?, '+5 minutes')
                ORDER BY datetime(date || ' ' || heure)
            """, (self.user_id, now, now))
            
            appointments = [dict(row) for row in cursor.fetchall()]
        
        return appointments