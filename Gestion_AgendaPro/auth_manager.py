import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from database_manager import db_connection
import sqlite3
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")  # Clé secrète depuis l'environnement
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

logger = logging.getLogger(__name__)

class AuthManager:
    """Gère l'authentification et l'autorisation"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe avec bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe contre son hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Crée un JWT token d'accès"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Vérifie un JWT token et retourne les données"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        """Authentifie un utilisateur"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash FROM utilisateurs WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and AuthManager.verify_password(password, user["password_hash"]):
                return dict(user)
            return None
    
    @staticmethod
    def get_current_user(token: str) -> Optional[Dict]:
        """Récupère l'utilisateur courant à partir du token"""
        payload = AuthManager.verify_token(token)
        if not payload:
            return None
        
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email FROM utilisateurs WHERE id = ?",
                (payload.get("sub"),)
            )
            user = cursor.fetchone()
            return dict(user) if user else None
    
    @staticmethod
    def create_user(username: str, password: str, email: str) -> Optional[int]:
        """Crée un nouvel utilisateur"""
        with db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO utilisateurs (username, password_hash, email) VALUES (?, ?, ?)",
                    (username, AuthManager.hash_password(password), email)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                logger.error("Username or email already exists")
                return None
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> bool:
        """Change le mot de passe d'un utilisateur"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM utilisateurs WHERE id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if user and AuthManager.verify_password(old_password, user["password_hash"]):
                new_hash = AuthManager.hash_password(new_password)
                cursor.execute(
                    "UPDATE utilisateurs SET password_hash = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                conn.commit()
                return True
            return False