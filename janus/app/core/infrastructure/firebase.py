import logging

import firebase_admin
from firebase_admin import credentials, db, firestore

logger = logging.getLogger(__name__)


class FirebaseService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, service_account_path: str, database_url: str | None = None):
        if self._initialized:
            return

        try:
            cred = credentials.Certificate(service_account_path)
            options = {}
            if database_url:
                options["databaseURL"] = database_url

            firebase_admin.initialize_app(cred, options)
            self._client = firestore.client()
            logger.info("Firebase Admin initialized successfully.")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise e

    def get_firestore(self):
        if not self._initialized:
            raise RuntimeError("Firebase not initialized. Call initialize() first.")
        return self._client

    def get_database(self):
        if not self._initialized:
            raise RuntimeError("Firebase not initialized. Call initialize() first.")
        # db reference root
        return db.reference()


def get_firebase_service() -> FirebaseService:
    return FirebaseService()
