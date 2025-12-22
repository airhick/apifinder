#!/usr/bin/env python3
"""
Script pour exécuter le crawler directement depuis le terminal
(sans interface web)
"""
import sys
import os
from downloader import bulk_downloader

if __name__ == "__main__":
    print("🚀 Démarrage du crawler depuis le terminal...")
    print("💡 Appuyez sur Ctrl+C une fois pour arrêter proprement\n")
    
    try:
        bulk_downloader()
    except KeyboardInterrupt:
        # Signal handler already handles this, but catch it here too
        print("\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)

