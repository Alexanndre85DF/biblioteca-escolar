import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração do Firebase
firebase_config = {
    "apiKey": "AIzaSyD9eHn3ZoH9Q0tJx8MR28H2SYGaOGRhbok",
    "authDomain": "biblioteca-escolar-35d25.firebaseapp.com",
    "projectId": "biblioteca-escolar-35d25",
    "storageBucket": "biblioteca-escolar-35d25.firebasestorage.app",
    "messagingSenderId": "798454574937",
    "appId": "1:798454574937:web:4b740627d39361847ea648"
}

# Inicializar Firebase Admin SDK
try:
    # Se já foi inicializado, não inicializa novamente
    firebase_admin.get_app()
except ValueError:
    # Inicializa o Firebase Admin SDK
    cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
    firebase_admin.initialize_app(cred)

# Obter instância do Firestore
db = firestore.client()

def get_firestore_db():
    return db 