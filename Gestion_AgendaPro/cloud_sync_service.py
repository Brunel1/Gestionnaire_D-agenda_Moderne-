import threading
import time
import requests
import json
from datetime import datetime
import logging
from dotenv import load_dotenv
import os
from queue import Queue
from typing import Dict, List, Optional
from database_manager import db_connection

load_dotenv()

class CloudSyncManager:
    """Gère la synchronisation avec le cloud"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.running = True
        self.sync_queue = Queue()
        self.sync_status = "disconnected"
        self.last_sync = None
        self.conflict_resolution = "server"  # or "local"
        
        # Configuration de l'API
        self.api_url = os.getenv("CLOUD_API_URL", "https://api.agenda-service.com/v1")
        self.api_key = os.getenv("CLOUD_API_KEY")
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", 3600))  # en secondes
        
        # Thread de synchronisation
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.event_thread = threading.Thread(target=self._process_events, daemon=True)
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        
    def start(self) -> None:
        """Démarre les services de synchronisation"""
        if self.api_key:
            self.sync_thread.start()
            self.event_thread.start()
            self.logger.info("Cloud sync service started")
        else:
            self.logger.warning("Cloud sync disabled - no API key configured")
    
    def stop(self) -> None:
        """Arrête les services de synchronisation"""
        self.running = False
        if self.sync_thread.is_alive():
            self.sync_thread.join()
        if self.event_thread.is_alive():
            self.event_thread.join()
        self.logger.info("Cloud sync service stopped")
    
    def queue_sync_event(self, event_type: str, data: Dict) -> None:
        """Ajoute un événement à synchroniser"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.sync_queue.put(event)
        self.logger.debug(f"Queued sync event: {event_type}")
    
    def _process_events(self) -> None:
        """Traite les événements en attente de synchronisation"""
        while self.running:
            try:
                if not self.sync_queue.empty():
                    event = self.sync_queue.get()
                    self._process_event(event)
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Event processing error: {e}")
                time.sleep(30)
    
    def _process_event(self, event: Dict) -> None:
        """Traite un événement individuel"""
        try:
            if event["type"] == "appointment_create":
                self._sync_create_appointment(event["data"])
            elif event["type"] == "appointment_update":
                self._sync_update_appointment(event["data"])
            elif event["type"] == "appointment_delete":
                self._sync_delete_appointment(event["data"])
            elif event["type"] == "share_create":
                self._sync_create_share(event["data"])
            elif event["type"] == "share_delete":
                self._sync_delete_share(event["data"])
        except Exception as e:
            self.logger.error(f"Failed to process event {event['type']}: {e}")
    
    def _sync_loop(self) -> None:
        """Boucle principale de synchronisation"""
        while self.running:
            try:
                self._full_sync()
                time.sleep(self.sync_interval)
            except Exception as e:
                self.logger.error(f"Sync error: {e}")
                time.sleep(300)  # Réessayer après 5 minutes en cas d'erreur
    
    def _full_sync(self) -> None:
        """Effectue une synchronisation complète"""
        if not self.api_key:
            return
        
        self.sync_status = "syncing"
        self.logger.info("Starting full sync")
        
        try:
            # 1. Envoyer les modifications locales
            local_changes = self._get_local_changes()
            if local_changes:
                self._send_changes_to_cloud(local_changes)
            
            # 2. Récupérer les modifications du cloud
            cloud_changes = self._get_cloud_changes()
            if cloud_changes:
                self._apply_cloud_changes(cloud_changes)
            
            # 3. Marquer comme synchronisé
            self.last_sync = datetime.now()
            self.sync_status = "synced"
            self.logger.info(f"Sync completed at {self.last_sync}")
            
        except Exception as e:
            self.sync_status = "error"
            self.logger.error(f"Sync failed: {e}")
            raise
    
    def _get_local_changes(self) -> Dict:
        """Récupère les modifications locales non synchronisées"""
        changes = {
            "appointments": [],
            "shares": []
        }
        
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Rendez-vous modifiés localement
            cursor.execute("""
                SELECT * FROM rendez_vous 
                WHERE utilisateur_id = ? AND last_modified > last_synced
            """, (self.user_id,))
            
            for row in cursor.fetchall():
                changes["appointments"].append(dict(row))
            
            # Partages modifiés localement
            cursor.execute("""
                SELECT p.* FROM partages p
                JOIN rendez_vous r ON p.rdv_id = r.id
                WHERE r.utilisateur_id = ? AND p.last_modified > p.last_synced
            """, (self.user_id,))
            
            for row in cursor.fetchall():
                changes["shares"].append(dict(row))
        
        return changes
    
    def _send_changes_to_cloud(self, changes: Dict) -> bool:
        """Envoie les modifications locales au cloud"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/sync/push",
                headers=headers,
                json=changes,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self._mark_changes_as_synced(changes)
                    return True
            
            self.logger.error(f"Failed to push changes: {response.text}")
            return False
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error during sync: {e}")
            return False
    
    def _mark_changes_as_synced(self, changes: Dict) -> None:
        """Marque les modifications comme synchronisées dans la base locale"""
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Mettre à jour les rendez-vous synchronisés
            appointment_ids = [a["id"] for a in changes.get("appointments", [])]
            if appointment_ids:
                cursor.execute(f"""
                    UPDATE rendez_vous 
                    SET last_synced = CURRENT_TIMESTAMP
                    WHERE id IN ({','.join(['?']*len(appointment_ids))})
                """, appointment_ids)
            
            # Mettre à jour les partages synchronisés
            share_ids = [s["id"] for s in changes.get("shares", [])]
            if share_ids:
                cursor.execute(f"""
                    UPDATE partages 
                    SET last_synced = CURRENT_TIMESTAMP
                    WHERE id IN ({','.join(['?']*len(share_ids))})
                """, share_ids)
            
            conn.commit()
    
    def _get_cloud_changes(self) -> Dict:
        """Récupère les modifications depuis le cloud"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/sync/pull?user_id={self.user_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("changes", {})
            
            self.logger.error(f"Failed to pull changes: {response.text}")
            return {}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error during sync: {e}")
            return {}
    
    def _apply_cloud_changes(self, changes: Dict) -> None:
        """Applique les modifications du cloud localement"""
        from database import (
            add_appointment, update_appointment, delete_appointment,
            share_appointment
        )
        
        try:
            # Appliquer les modifications des rendez-vous
            for appointment in changes.get("appointments", []):
                action = appointment.get("action")
                
                if action == "create":
                    add_appointment(
                        user_id=self.user_id,
                        date=appointment["date"],
                        time=appointment["heure"],
                        title=appointment["titre"],
                        description=appointment.get("description", ""),
                        category=appointment.get("categorie", "Autre"),
                        reminder=appointment.get("rappel", 0),
                        recurrence=appointment.get("recurrence"),
                        recurrence_end=appointment.get("recurrence_end")
                    )
                elif action == "update":
                    update_appointment(
                        rdv_id=appointment["id"],
                        new_title=appointment["titre"],
                        new_description=appointment.get("description", ""),
                        new_category=appointment.get("categorie", "Autre"),
                        reminder=appointment.get("rappel", 0),
                        recurrence=appointment.get("recurrence"),
                        recurrence_end=appointment.get("recurrence_end")
                    )
                elif action == "delete":
                    delete_appointment(appointment["id"])
            
            # Appliquer les modifications des partages
            for share in changes.get("shares", []):
                action = share.get("action")
                
                if action in ["create", "update"]:
                    share_appointment(
                        rdv_id=share["rdv_id"],
                        owner_id=share["owner_id"],
                        recipient_id=self.user_id,
                        permissions=share["permissions"]
                    )
                elif action == "delete":
                    # Implémenter la suppression du partage si nécessaire
                    pass
            
            self.logger.info(f"Applied {len(changes.get('appointments', []))} cloud changes")
            
        except Exception as e:
            self.logger.error(f"Failed to apply cloud changes: {e}")
            raise
    
    def _sync_create_appointment(self, appointment: Dict) -> None:
        """Synchronise la création d'un rendez-vous"""
        self._sync_with_retry({
            "type": "appointment",
            "action": "create",
            "data": appointment
        })
    
    def _sync_update_appointment(self, appointment: Dict) -> None:
        """Synchronise la mise à jour d'un rendez-vous"""
        self._sync_with_retry({
            "type": "appointment",
            "action": "update",
            "data": appointment
        })
    
    def _sync_delete_appointment(self, appointment_id: int) -> None:
        """Synchronise la suppression d'un rendez-vous"""
        self._sync_with_retry({
            "type": "appointment",
            "action": "delete",
            "data": {"id": appointment_id}
        })
    
    def _sync_create_share(self, share: Dict) -> None:
        """Synchronise la création d'un partage"""
        self._sync_with_retry({
            "type": "share",
            "action": "create",
            "data": share
        })
    
    def _sync_delete_share(self, share_id: int) -> None:
        """Synchronise la suppression d'un partage"""
        self._sync_with_retry({
            "type": "share",
            "action": "delete",
            "data": {"id": share_id}
        })
    
    def _sync_with_retry(self, payload: Dict, max_retries: int = 3) -> bool:
        """Tente une synchronisation avec reprise en cas d'échec"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/sync/event",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return True
                
                self.logger.warning(
                    f"Sync attempt {attempt+1} failed for {payload['type']}: {response.text}"
                )
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(
                    f"Sync attempt {attempt+1} failed for {payload['type']}: {e}"
                )
            
            time.sleep(5 * (attempt + 1))  # Attente exponentielle
        
        self.logger.error(f"Failed to sync {payload['type']} after {max_retries} attempts")
        return False
    
    def get_sync_status(self) -> Dict:
        """Retourne l'état actuel de la synchronisation"""
        return {
            "status": self.sync_status,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "queue_size": self.sync_queue.qsize()
        }