#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Blogger feeder with history:
- Picks 2 categories per UTC day sequentially
- Avoids repeating categories within the same day
- Loops back to top when reaching the end
- Generates unique titles, meta descriptions, and articles
- Avoids repeating content used in last 7 articles per category
- Tracks history in .data/blog_history.json
- Emails each article to Blogger
"""

import os
import ssl
import smtplib
import json
import hashlib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import google.generativeai as genai

# ---------------- CONFIG ----------------
BLOGGER_MAIL = os.environ["BLOGGER_SECRET_MAIL"]
GMAIL_USER   = os.environ["GMAIL_USER"]
GMAIL_PASS   = os.environ["GMAIL_PASS"]

genai.configure(api_key=os.environ["GEMINI_API_KEY"]) 
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
HISTORY_FILE = os.getenv("HISTORY_FILE", ".data/blog_history.json")
ARTICLES_PER_DAY = int(os.getenv("ARTICLES_PER_DAY", "2"))
MAX_RETRIES_TITLE = int(os.getenv("MAX_RETRIES_TITLE", "5"))

# ---------------- CATEGORIES (UPDATED FROM USER) ----------------
CATEGORIES = [
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment protéger un compte Facebook contre le piratage",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Reconnaître et éviter les fausses pages Facebook (phishing)",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment sécuriser un compte Instagram avec l’authentification à deux facteurs",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Identifier un email frauduleux et éviter les arnaques en ligne",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Vérifier si un lien est sûr avant de cliquer",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment chiffrer ses messages avec Signal ou WhatsApp",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Activer la vérification en deux étapes sur Gmail",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Bloquer la publicité intrusive sur son smartphone",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Sauvegarder ses données pour éviter les pertes",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Protéger ses photos avec un mot de passe sur iOS et Android",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Éviter les virus en naviguant sur Internet",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Sécuriser un réseau Wi-Fi domestique",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Reconnaître un site frauduleux (.onion et dark web)",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Supprimer un virus de son PC avec Windows Defender",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Sécuriser sa clé USB contre les infections",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment repérer un compte WhatsApp frauduleux",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Supprimer un logiciel malveillant de son téléphone",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment détecter un malware sur Android",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Gérer ses mots de passe avec un gestionnaire sécurisé",
    "SÉCURITÉ INFORMATIQUE ET PROTECTION DES DONNÉES - Comment éviter le vol d’identité en ligne",

    "ASTUCES ET PRODUCTIVITÉ - Créer un dossier invisible sur Windows",
    "ASTUCES ET PRODUCTIVITÉ - Créer un dossier sans nom sur PC",
    "ASTUCES ET PRODUCTIVITÉ - Rouvrir un onglet fermé dans Chrome ou Firefox",
    "ASTUCES ET PRODUCTIVITÉ - Télécharger des vidéos YouTube légalement avec YouTube Premium",
    "ASTUCES ET PRODUCTIVITÉ - Utiliser Google Drive pour stocker ses fichiers gratuitement",
    "ASTUCES ET PRODUCTIVITÉ - Accéder à son PC depuis un smartphone Android",
    "ASTUCES ET PRODUCTIVITÉ - Convertir un fichier PDF en Word gratuitement",
    "ASTUCES ET PRODUCTIVITÉ - Masquer un fichier sur Android sans application",
    "ASTUCES ET PRODUCTIVITÉ - Compresser des images sans perte de qualité",
    "ASTUCES ET PRODUCTIVITÉ - Créer une adresse email temporaire",
    "ASTUCES ET PRODUCTIVITÉ - Télécharger ses photos iCloud sur PC",
    "ASTUCES ET PRODUCTIVITÉ - Convertir une page web en fichier PDF",
    "ASTUCES ET PRODUCTIVITÉ - Utiliser Google Keep pour prendre des notes rapides",
    "ASTUCES ET PRODUCTIVITÉ - Avoir ses notifications Android sur PC",
    "ASTUCES ET PRODUCTIVITÉ - Traduire instantanément un texte avec Google Lens",
    "ASTUCES ET PRODUCTIVITÉ - Scanner un document avec son smartphone",
    "ASTUCES ET PRODUCTIVITÉ - Partager un gros fichier sans email",
    "ASTUCES ET PRODUCTIVITÉ - Faire une capture d’écran défilante sur Android",
    "ASTUCES ET PRODUCTIVITÉ - Utiliser un VPN pour protéger sa connexion",
    "ASTUCES ET PRODUCTIVITÉ - Trouver l’emplacement où une photo a été prise",

    "MAINTENANCE ET DÉPANNAGE - Réparer une clé USB corrompue",
    "MAINTENANCE ET DÉPANNAGE - Supprimer un virus raccourci sur clé USB",
    "MAINTENANCE ET DÉPANNAGE - Retrouver des photos supprimées sur Android",
    "MAINTENANCE ET DÉPANNAGE - Sauvegarder un message WhatsApp important",
    "MAINTENANCE ET DÉPANNAGE - Accélérer son PC sous Windows",
    "MAINTENANCE ET DÉPANNAGE - Libérer de l’espace sur son smartphone",
    "MAINTENANCE ET DÉPANNAGE - Désactiver les notifications intrusives sur Chrome",
    "MAINTENANCE ET DÉPANNAGE - Réinitialiser un téléphone Android bloqué (méthode officielle)",
    "MAINTENANCE ET DÉPANNAGE - Mettre à jour Windows sans perdre ses fichiers",
    "MAINTENANCE ET DÉPANNAGE - Utiliser Hiren’s BootCD pour dépanner un PC",
    "MAINTENANCE ET DÉPANNAGE - Vérifier la santé d’un disque dur",
    "MAINTENANCE ET DÉPANNAGE - Changer le mot de passe Windows oublié (méthode légale)",
    "MAINTENANCE ET DÉPANNAGE - Supprimer un logiciel qui refuse de se désinstaller",
    "MAINTENANCE ET DÉPANNAGE - Récupérer ses données après un formatage",
    "MAINTENANCE ET DÉPANNAGE - Améliorer la vitesse de chargement de son smartphone",
    "MAINTENANCE ET DÉPANNAGE - Optimiser la batterie d’un téléphone Android",
    "MAINTENANCE ET DÉPANNAGE - Réparer un fichier corrompu",
    "MAINTENANCE ET DÉPANNAGE - Utiliser un antivirus gratuit efficace",
    "MAINTENANCE ET DÉPANNAGE - Sauvegarder automatiquement ses fichiers importants",
    "MAINTENANCE ET DÉPANNAGE - Réparer une connexion Internet lente",

    "PROGRAMMATION ET DÉVELOPPEMENT - Apprendre les bases du langage HTML",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer une page web simple avec HTML et CSS",
    "PROGRAMMATION ET DÉVELOPPEMENT - Comprendre le JavaScript en 10 minutes",
    "PROGRAMMATION ET DÉVELOPPEMENT - Apprendre à créer un script Python de base",
    "PROGRAMMATION ET DÉVELOPPEMENT - Faire une calculatrice simple en Python",
    "PROGRAMMATION ET DÉVELOPPEMENT - Développer un formulaire de contact en HTML/PHP",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer un bouton animé en CSS",
    "PROGRAMMATION ET DÉVELOPPEMENT - Comprendre l’algorithme",
    "PROGRAMMATION ET DÉVELOPPEMENT - Utiliser ChatGPT pour générer du code",
    "PROGRAMMATION ET DÉVELOPPEMENT - Introduction aux bases de données MySQL",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer un mini-jeu avec Scratch",
    "PROGRAMMATION ET DÉVELOPPEMENT - Faire un script qui renomme plusieurs fichiers automatiquement",
    "PROGRAMMATION ET DÉVELOPPEMENT - Apprendre à utiliser Git et GitHub",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer un générateur de mot de passe sécurisé en Python",
    "PROGRAMMATION ET DÉVELOPPEMENT - Afficher l’heure et la date en JavaScript",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer une page responsive avec Bootstrap",
    "PROGRAMMATION ET DÉVELOPPEMENT - Faire un bot Telegram simple en Python",
    "PROGRAMMATION ET DÉVELOPPEMENT - Comprendre les API et comment les utiliser",
    "PROGRAMMATION ET DÉVELOPPEMENT - Envoyer un email automatiquement avec Python",
    "PROGRAMMATION ET DÉVELOPPEMENT - Créer un convertisseur d’unités en JavaScript",

    "CLOUD, STOCKAGE ET SYNCHRONISATION - Sauvegarder automatiquement ses photos sur Google Photos",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Utiliser Dropbox pour partager un fichier",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Obtenir 15 Go gratuits sur Google Drive",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Organiser ses fichiers sur OneDrive",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Synchroniser ses documents entre PC et smartphone",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Sauvegarder un site web pour le consulter hors ligne",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Utiliser iCloud pour sauvegarder ses données iPhone",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Compresser des fichiers avant de les envoyer par email",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Utiliser WeTransfer pour envoyer des fichiers volumineux",
    "CLOUD, STOCKAGE ET SYNCHRONISATION - Partager un dossier complet sur Google Drive",

    "ANDROID ET IOS – ASTUCES - Installer une application Android en APK de manière sécurisée",
    "ANDROID ET IOS – ASTUCES - Supprimer le cache d’une application sur Android",
    "ANDROID ET IOS – ASTUCES - Créer un dossier d’applications sur l’écran d’accueil iOS",
    "ANDROID ET IOS – ASTUCES - Utiliser Siri pour automatiser une action",
    "ANDROID ET IOS – ASTUCES - Faire un enregistrement d’écran sur iPhone",
    "ANDROID ET IOS – ASTUCES - Programmer l’envoi d’un SMS sur Android",
    "ANDROID ET IOS – ASTUCES - Utiliser le mode économie d’énergie sur iOS",
    "ANDROID ET IOS – ASTUCES - Mettre à jour manuellement Android",
    "ANDROID ET IOS – ASTUCES - Retrouver un iPhone perdu avec Localiser mon iPhone",
    "ANDROID ET IOS – ASTUCES - Cloner l’écran de son téléphone sur une TV",
    "ANDROID ET IOS – ASTUCES - Désactiver les applications en arrière-plan pour économiser la batterie",
    "ANDROID ET IOS – ASTUCES - Utiliser Google Assistant efficacement",
    "ANDROID ET IOS – ASTUCES - Libérer de l’espace sur iPhone sans supprimer de photos",
    "ANDROID ET IOS – ASTUCES - Activer le mode sombre sur Android et iOS",
    "ANDROID ET IOS – ASTUCES - Installer une police personnalisée sur Android",
    "ANDROID ET IOS – ASTUCES - Gérer les autorisations d’application sur Android",
    "ANDROID ET IOS – ASTUCES - Transférer ses données d’iPhone vers Android",
    "ANDROID ET IOS – ASTUCES - Scanner un QR Code sans application",
    "ANDROID ET IOS – ASTUCES - Retrouver les applications récemment supprimées",
    "ANDROID ET IOS – ASTUCES - Empêcher une application d’utiliser vos données mobiles",

    "BUREAUTIQUE ET OUTILS - Créer un tableau Excel avec formules simples",
    "BUREAUTIQUE ET OUTILS - Utiliser Word pour créer un CV",
    "BUREAUTIQUE ET OUTILS - Faire une présentation PowerPoint dynamique",
    "BUREAUTIQUE ET OUTILS - Convertir un fichier Word en PDF",
    "BUREAUTIQUE ET OUTILS - Ajouter un graphique dans Excel",
    "BUREAUTIQUE ET OUTILS - Utiliser Google Docs pour travailler en ligne",
    "BUREAUTIQUE ET OUTILS - Mettre un mot de passe sur un fichier Word",
    "BUREAUTIQUE ET OUTILS - Faire un publipostage dans Word",
    "BUREAUTIQUE ET OUTILS - Traduire un document Word automatiquement",
    "BUREAUTIQUE ET OUTILS - Créer un planning dans Google Sheets",
    "BUREAUTIQUE ET OUTILS - Fusionner deux PDF gratuitement",
    "BUREAUTIQUE ET OUTILS - Extraire des images d’un PDF",
    "BUREAUTIQUE ET OUTILS - Créer un formulaire Google Forms",
    "BUREAUTIQUE ET OUTILS - Compresser un PDF pour réduire sa taille",
    "BUREAUTIQUE ET OUTILS - Supprimer les doublons dans Excel",
    "BUREAUTIQUE ET OUTILS - Utiliser les macros dans Excel",
    "BUREAUTIQUE ET OUTILS - Insérer une vidéo dans PowerPoint",
    "BUREAUTIQUE ET OUTILS - Partager un document Word pour travailler à plusieurs",
    "BUREAUTIQUE ET OUTILS - Convertir un PowerPoint en vidéo",
    "BUREAUTIQUE ET OUTILS - Ajouter des commentaires dans un document Word",

    "CRÉATION DE CONTENU ET MULTIMÉDIA - Monter une vidéo avec CapCut",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer une miniature YouTube avec Canva",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Enregistrer sa voix sur PC",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Faire un podcast depuis son téléphone",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Ajouter des sous-titres à une vidéo",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Utiliser OBS Studio pour filmer son écran",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer un diaporama photo avec musique",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Retoucher une image avec Photopea (gratuit)",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer un GIF animé à partir d’une vidéo",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Enregistrer une réunion Zoom",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Optimiser une vidéo pour TikTok",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Couper un extrait d’une vidéo",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Ajouter un filigrane à une image",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer un logo gratuitement en ligne",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Enregistrer une vidéo en slow motion",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Supprimer l’arrière-plan d’une photo",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer un collage photo sur mobile",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Utiliser InShot pour éditer des vidéos",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Faire un montage audio simple",
    "CRÉATION DE CONTENU ET MULTIMÉDIA - Créer une bannière pour un réseau social",

    "INTERNET ET NAVIGATION - Activer le mode lecteur dans un navigateur",
    "INTERNET ET NAVIGATION - Utiliser les favoris pour retrouver un site rapidement",
    "INTERNET ET NAVIGATION - Rechercher efficacement sur Google",
    "INTERNET ET NAVIGATION - Sauvegarder les mots de passe dans Chrome",
    "INTERNET ET NAVIGATION - Activer la traduction automatique dans Chrome",
    "INTERNET ET NAVIGATION - Installer une extension sur Firefox",
    "INTERNET ET NAVIGATION - Utiliser le mode navigation privée",
    "INTERNET ET NAVIGATION - Gérer plusieurs onglets facilement",
    "INTERNET ET NAVIGATION - Bloquer les cookies publicitaires",
    "INTERNET ET NAVIGATION - Télécharger une page web en PDF",
    "INTERNET ET NAVIGATION - Vérifier la vitesse de sa connexion Internet",
    "INTERNET ET NAVIGATION - Rechercher une image sur Google à partir d’une photo",
    "INTERNET ET NAVIGATION - Utiliser un bloqueur de pop-up",
    "INTERNET ET NAVIGATION - Créer un raccourci vers un site web sur le bureau",
    "INTERNET ET NAVIGATION - Utiliser Google Alerts pour surveiller un sujet",
    "INTERNET ET NAVIGATION - Consulter l’historique d’un site avec Wayback Machine",
    "INTERNET ET NAVIGATION - Sauvegarder ses favoris pour les importer ailleurs",
    "INTERNET ET NAVIGATION - Ouvrir automatiquement plusieurs onglets au démarrage",
    "INTERNET ET NAVIGATION - Utiliser un outil de capture d’écran web",
    "INTERNET ET NAVIGATION - Consulter les statistiques d’un site web",

    "CYBERSÉCURITÉ AVANCÉE - Comprendre le chiffrement AES",
    "CYBERSÉCURITÉ AVANCÉE - Créer un mot de passe fort et mémorisable",
    "CYBERSÉCURITÉ AVANCÉE - Activer un pare-feu sur Windows et macOS",
    "CYBERSÉCURITÉ AVANCÉE - Détecter une tentative de phishing par SMS",
    "CYBERSÉCURITÉ AVANCÉE - Utiliser l’authentification biométrique",
    "CYBERSÉCURITÉ AVANCÉE - Sauvegarder ses données sur un disque externe sécurisé",
    "CYBERSÉCURITÉ AVANCÉE - Protéger un fichier ZIP par mot de passe",
    "CYBERSÉCURITÉ AVANCÉE - Apprendre les bases du RGPD",
    "CYBERSÉCURITÉ AVANCÉE - Sécuriser ses comptes avec Authy",
    "CYBERSÉCURITÉ AVANCÉE - Comprendre les ransomwares et comment s’en protéger",
    "CYBERSÉCURITÉ AVANCÉE - Mettre à jour ses logiciels pour éviter les failles",
    "CYBERSÉCURITÉ AVANCÉE - Utiliser un antivirus gratuit fiable",
    "CYBERSÉCURITÉ AVANCÉE - Chiffrer un disque dur externe",
    "CYBERSÉCURITÉ AVANCÉE - Protéger sa webcam contre le piratage",
    "CYBERSÉCURITÉ AVANCÉE - Vérifier si ses données ont fuité avec HaveIBeenPwned",
    "CYBERSÉCURITÉ AVANCÉE - Configurer la sécurité sur LinkedIn",
    "CYBERSÉCURITÉ AVANCÉE - Supprimer ses anciennes publications sensibles",
    "CYBERSÉCURITÉ AVANCÉE - Éviter les réseaux Wi-Fi publics non sécurisés",
    "CYBERSÉCURITÉ AVANCÉE - Gérer les permissions d’une application mobile",
    "CYBERSÉCURITÉ AVANCÉE - Reconnaître une fausse application sur le Play Store",

    "TECHNOLOGIE ET PROJETS DIY - Créer un serveur Minecraft privé",
    "TECHNOLOGIE ET PROJETS DIY - Installer une imprimante sur un réseau Wi-Fi",
    "TECHNOLOGIE ET PROJETS DIY - Fabriquer un support de téléphone maison",
    "TECHNOLOGIE ET PROJETS DIY - Utiliser une Raspberry Pi comme mini-ordinateur",
    "TECHNOLOGIE ET PROJETS DIY - Créer une horloge connectée avec Arduino",
    "TECHNOLOGIE ET PROJETS DIY - Faire une lampe LED pilotée par smartphone",
    "TECHNOLOGIE ET PROJETS DIY - Transformer un vieux PC en serveur de fichiers",
    "TECHNOLOGIE ET PROJETS DIY - Configurer une caméra de sécurité IP",
    "TECHNOLOGIE ET PROJETS DIY - Construire un système d’arrosage automatique avec Arduino",
    "TECHNOLOGIE ET PROJETS DIY - Installer un système domotique simple",
    "TECHNOLOGIE ET PROJETS DIY - Connecter une manette de jeu à son téléphone",
    "TECHNOLOGIE ET PROJETS DIY - Faire une borne d’arcade maison",
    "TECHNOLOGIE ET PROJECTS DIY - Transformer un écran de PC en TV",
    "TECHNOLOGIE ET PROJETS DIY - Construire un haut-parleur Bluetooth maison",
    "TECHNOLOGIE ET PROJETS DIY - Installer un détecteur de mouvement connecté",
    "TECHNOLOGIE ET PROJETS DIY - Utiliser un capteur de température connecté",
    "TECHNOLOGIE ET PROJETS DIY - Monter un PC de A à Z",
    "TECHNOLOGIE ET PROJETS DIY - Optimiser un vieux PC pour qu’il soit plus rapide",
    "TECHNOLOGIE ET PROJETS DIY - Créer un NAS avec un Raspberry Pi",
    "TECHNOLOGIE ET PROJETS DIY - Installer un assistant vocal open source",

    "OUTILS ET SERVICES EN LIGNE - Créer un sondage avec Strawpoll",
    "OUTILS ET SERVICES EN LIGNE - Convertir un fichier audio en texte",
    "OUTILS ET SERVICES EN LIGNE - Faire un test de vitesse Internet avec Speedtest",
    "OUTILS ET SERVICES EN LIGNE - Retirer un arrière-plan d’image gratuitement",
    "OUTILS ET SERVICES EN LIGNE - Redimensionner une image en ligne",
    "OUTILS ET SERVICES EN LIGNE - Convertir une vidéo en MP3 légalement",
    "OUTILS ET SERVICES EN LIGNE - Créer un QR Code personnalisé",
    "OUTILS ET SERVICES EN LIGNE - Utiliser un planificateur de publications sur réseaux sociaux",
    "OUTILS ET SERVICES EN LIGNE - Faire une capture d’écran longue sur mobile",
    "OUTILS ET SERVICES EN LIGNE - Créer une signature électronique",
    "OUTILS ET SERVICES EN LIGNE - Utiliser Trello pour gérer ses projets",
    "OUTILS ET SERVICES EN LIGNE - Créer un organigramme en ligne",
    "OUTILS ET SERVICES EN LIGNE - Éditer un fichier PDF directement dans le navigateur",
    "OUTILS ET SERVICES EN LIGNE - Vérifier l’orthographe d’un texte automatiquement",
    "OUTILS ET SERVICES EN LIGNE - Créer un calendrier partagé en ligne",
    "OUTILS ET SERVICES EN LIGNE - Sauvegarder ses mots de passe sur un coffre-fort en ligne",
    "OUTILS ET SERVICES EN LIGNE - Utiliser Google Trends pour analyser un sujet",
    "OUTILS ET SERVICES EN LIGNE - Créer un lien court avec Bitly",
    "OUTILS ET SERVICES EN LIGNE - Générer une infographie en ligne",
    "OUTILS ET SERVICES EN LIGNE - Organiser un événement avec Eventbrite",

    "FORMATION ET APPRENTISSAGE - Apprendre à taper plus vite au clavier",
    "FORMATION ET APPRENTISSAGE - Comprendre les bases du référencement SEO",
    "FORMATION ET APPRENTISSAGE - Apprendre les notions de base du marketing digital",
    "FORMATION ET APPRENTISSAGE - Lire un livre gratuitement sur Internet Archive",
    "FORMATION ET APPRENTISSAGE - Suivre un cours gratuit sur OpenClassrooms",
    "FORMATION ET APPRENTISSAGE - Apprendre l’anglais avec Duolingo",
    "FORMATION ET APPRENTISSAGE - Apprendre les mathématiques avec Khan Academy",
    "FORMATION ET APPRENTISSAGE - Découvrir les bases de la finance personnelle",
    "FORMATION ET APPRENTISSAGE - Apprendre la retouche photo gratuitement",
    "FORMATION ET APPRENTISSAGE - Comprendre les bases de la cybersécurité",
    "FORMATION ET APPRENTISSAGE - Apprendre à utiliser Canva pour le design",
    "FORMATION ET APPRENTISSAGE - Suivre une formation gratuite sur Coursera",
    "FORMATION ET APPRENTISSAGE - Apprendre la gestion de projet",
    "FORMATION ET APPRENTISSAGE - Comprendre le fonctionnement de la blockchain",
    "FORMATION ET APPRENTISSAGE - Apprendre les bases du montage vidéo",
    "FORMATION ET APPRENTISSAGE - Apprendre à coder en Java",
    "FORMATION ET APPRENTISSAGE - Apprendre les bases de Linux",
    "FORMATION ET APPRENTISSAGE - Apprendre à configurer un serveur web",
    "FORMATION ET APPRENTISSAGE - Comprendre le fonctionnement du cloud computing",
    "FORMATION ET APPRENTISSAGE - Suivre une formation sur la protection des données",

    "HACKING ÉTHIQUE & SÉCURITÉ - Comment scanner un site avec Nikto",
    "HACKING ÉTHETIQUE & SÉCURITÉ - Exploitation d’une faille LFI pas à pas",
    "HACKING ÉTHIQUE & SÉCURITÉ - Utiliser Hydra pour brute-forcer un compte FTP",
    "HACKING ÉTHIQUE & SÉCURITÉ - Apprendre à faire un phishing Facebook avec SocialFish",
    "HACKING ÉETHIQUE & SÉCURITÉ - Utiliser la commande whois pour obtenir des infos d’un domaine",
    "HACKING ÉTHIQUE & SÉCURITÉ - Récupérer les en-têtes HTTP avec Curl",
    "HACKING ÉTHIQUE & SÉCURITÉ - Simuler un DDoS sur un serveur local avec LOIC",
    "HACKING ÉTHIQUE & SÉCURITÉ - Bypasser un pare-feu avec proxychains",
    "HACKING ÉETHIQUE & SÉCURITÉ - Utiliser John The Ripper pour cracker un mot de passe Linux",
    "HACKING ÉETHIQUE & SÉCURITÉ - Exploiter une injection XML (XXE)",

    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Créer un script Python pour vérifier si un site est en ligne",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Automatiser la sauvegarde d’un site avec Python et FTP",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Script pour trouver les sous-domaines d’un site",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Automatiser un scan de ports avec Python",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Détecter une adresse IP publique via Python",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Créer un keylogger en Python (usage éthique uniquement)",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Générer des mots de passe forts en Python",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Script pour envoyer un email anonyme en Python",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Extraire les liens d’une page web avec BeautifulSoup",
    "PROGRAMMATION & SCRIPTS DE SÉCURITÉ - Convertir un script Python en exécutable Windows",

    "OSINT (OPEN SOURCE INTELLIGENCE) - Trouver l’adresse IP d’un site avec nslookup",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Utiliser theHarvester pour collecter des emails",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Analyse de profil Facebook avec Sherlock",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Rechercher un pseudo sur le dark web",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Retrouver les anciennes versions d’un site avec Wayback Machine",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Trouver l’emplacement approximatif d’une IP",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Recherche d’images inversée avec Google Lens",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Suivre un compte Twitter avec Twint",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Identifier un hébergeur de site web",
    "OSINT (OPEN SOURCE INTELLIGENCE) - Utiliser Maltego pour cartographier des données",

    "PENTESTING RÉSEAU - Analyse de paquets avec Wireshark",
    "PENTESTING RÉSEAU - Créer un faux point Wi-Fi avec Airbase-ng",
    "PENTESTING RÉSEAU - Capter les mots de passe sur un réseau non sécurisé",
    "PENTESTING RÉSEAU - Cracker un mot de passe WPA avec aircrack-ng",
    "PENTESTING RÉSEAU - Détecter les appareils connectés à un réseau",
    "PENTESTING RÉSEAU - Exploiter une vulnérabilité SMB avec Metasploit",
    "PENTESTING RÉSEAU - Simuler une attaque MITM (Man in the Middle)",
    "PENTESTING RÉSEAU - Bloquer l’accès internet à un appareil précis",
    "PENTESTING RÉSEAU - Faire un scan réseau avec Nmap",
    "PENTESTING RÉSEAU - Utiliser ARP Spoofing pour intercepter du trafic",

    "SÉCURITÉ WEB & BYPASS - Tester un site pour vulnérabilités XSS",
    "SÉCURITÉ WEB & BYPASS - Bypasser un login avec SQL Injection basique",
    "SÉCURITÉ WEB & BYPASS - Extraire des données via SQLMap",
    "SÉCURITÉ WEB & BYPASS - Upload malveillant et exécution PHP",
    "SÉCURITÉ WEB & BYPASS - Trouver des pages cachées d’un site avec Dirb",
    "SÉCURITÉ WEB & BYPASS - Détecter la version d’un CMS et ses failles",
    "SÉCURITÉ WEB & BYPASS - Exploiter une faille CSRF",
    "SÉCURITÉ WEB & BYPASS - Contourner Cloudflare pour obtenir IP réelle",
    "SÉCURITÉ WEB & BYPASS - Forcer le téléchargement d’un fichier protégé",
    "SÉCURITÉ WEB & BYPASS - Créer un script d’auto-login sur un site web",

    "SÉCURITÉ MOBILE & ANDROID - Rooter un téléphone Android (sécurité)",
    "SÉCURITÉ MOBILE & ANDROID - Extraire les données d’une application Android",
    "SÉCURITÉ MOBILE & ANDROID - Analyser les permissions d’une APK",
    "SÉCURITÉ MOBILE & ANDROID - Désassembler une APK avec JADX",
    "SÉCURITÉ MOBILE & ANDROID - Faire un sniffing réseau sur Android",
    "SÉCURITÉ MOBILE & ANDROID - Utiliser Termux pour lancer des scripts Python",
    "SÉCURITÉ MOBILE & ANDROID - Cloner une application Android",
    "SÉCURITÉ MOBILE & ANDROID - Installer Metasploit sur Android",
    "SÉCURITÉ MOBILE & ANDROID - Capter les SMS sur un appareil rooté",
    "SÉCURITÉ MOBILE & ANDROID - Supprimer un mot de passe d’écran sur Android (éthique)",

    "DARK WEB & ANONYMAT - Installer Tor sur PC et Android",
    "DARK WEB & ANONYMAT - Accéder à des .onion avec Tor Browser",
    "DARK WEB & ANONYMAT - Créer un serveur caché sur Tor",
    "DARK WEB & ANONYMAT - Utiliser Tails OS pour rester anonyme",
    "DARK WEB & ANONYMAT - Configurer un VPN sur routeur",
    "DARK WEB & ANONYMAT - Échanger des fichiers de manière chiffrée",
    "DARK WEB & ANONYMAT - Utiliser PGP pour chiffrer des messages",
    "DARK WEB & ANONYMAT - Masquer son IP avec un réseau proxy",
    "DARK WEB & ANONYMAT - Acheter en crypto de manière anonyme",
    "DARK WEB & ANONYMAT - Éviter le tracking sur les réseaux sociaux",

    "CYBERDÉFENSE & PRÉVENTION - Mettre en place un IDS avec Snort",
    "CYBERDÉFENSE & PRÉVENTION - Sauvegarder et chiffrer ses données avec VeraCrypt",
    "CYBERDÉFENSE & PRÉVENTION - Sécuriser son serveur Linux",
    "CYBERDÉFENSE & PRÉVENTION - Configurer un pare-feu sous Windows",
    "CYBERDÉFENSE & PRÉVENTION - Protéger ses comptes avec authentification à deux facteurs",
    "CYBERDÉFENSE & PRÉVENTION - Détecter un logiciel espion sur PC",
    "CYBERDÉFENSE & PRÉVENTION - Éviter les ransomwares",
    "CYBERDÉFENSE & PRÉVENTION - Nettoyer les métadonnées d’un fichier",
    "CYBERDÉFENSE & PRÉVENTION - Utiliser un gestionnaire de mots de passe sécurisé",
    "CYBERDÉFENSE & PRÉVENTION - Vérifier si ses données ont fuité (HaveIBeenPwned)",

    "HACKING ÉTHIQUE AVANCÉ - Exploiter une faille RCE (Remote Code Execution)",
    "HACKING ÉTHIQUE AVANCÉ - Chainer plusieurs failles pour un accès total",
    "HACKING ÉTHIQUE AVANCÉ - Analyse d’un malware inconnu",
    "HACKING ÉTHIQUE AVANCÉ - Évasion d’un antivirus",
    "HACKING ÉTHIQUE AVANCÉ - Exploiter une faille sur un IoT (caméra connectée)",
    "HACKING ÉTHIQUE AVANCÉ - Utiliser Burp Suite pour intercepter du trafic",
    "HACKING ÉTHIQUE AVANCÉ - Forger des requêtes HTTP manuelles",
    "HACKING ÉTHIQUE AVANCÉ - Énumération d’utilisateurs sur un site web",
    "HACKING ÉTHIQUE AVANCÉ - Exploitation d’une faille SSRF",
    "HACKING ÉTHIQUE AVANCÉ - Créer un backdoor Python chiffré",

    "DIVERS & AUTOMATISATION - Automatiser le téléchargement de fichiers via Python",
    "DIVERS & AUTOMATISATION - Scraper des résultats Google sans API",
    "DIVERS & AUTOMATISATION - Créer un bot Telegram pour envoyer des alertes",
    "DIVERS & AUTOMATISATION - Faire parler un bot avec IA locale",
    "DIVERS & AUTOMATISATION - Créer un ransomware éducatif en Python",
    "DIVERS & AUTOMATISATION - Automatiser le scan de plusieurs IP avec Nmap",
    "DIVERS & AUTOMATISATION - Script pour détecter un site down et envoyer une alerte",
    "DIVERS & AUTOMATISATION - Envoyer des messages programmés sur WhatsApp",
    "DIVERS & AUTOMATISATION - Créer un bot qui répond aux emails automatiquement",
    "DIVERS & AUTOMATISATION - Simuler un environnement Windows infecté pour formation",

        # DARK WEB & ANONYMAT
    "DARK WEB & ANONYMAT - Masquer son IP avec un réseau proxy",
    "DARK WEB & ANONYMAT - Vérifier son anonymat en ligne",
    "DARK WEB & ANONYMAT - Sécuriser sa messagerie sur le Dark Web",
    "DARK WEB & ANONYMAT - Configurer I2P pour la navigation anonyme",
    "DARK WEB & ANONYMAT - Créer un portefeuille crypto anonyme",
    "DARK WEB & ANONYMAT - Utiliser un bridge Tor pour contourner la censure",
    "DARK WEB & ANONYMAT - Héberger un blog anonyme",
    "DARK WEB & ANONYMAT - Différences entre Tor, I2P et Freenet",
    "DARK WEB & ANONYMAT - Accéder à des forums cachés en toute sécurité",
    "DARK WEB & ANONYMAT - Utiliser Whonix comme système d’exploitation anonyme",
    "DARK WEB & ANONYMAT - Naviguer sur le Dark Web en toute sécurité",
    "DARK WEB & ANONYMAT - Créer un compte anonyme sur un forum .onion",
    "DARK WEB & ANONYMAT - Les marketplaces légales sur le Dark Web",
    "DARK WEB & ANONYMAT - Sécuriser un disque externe pour Dark Web",
    "DARK WEB & ANONYMAT - Éviter les arnaques sur le Dark Web",
    "DARK WEB & ANONYMAT - Installer un bridge Tor pour contournement avancé",
    "DARK WEB & ANONYMAT - Comprendre les cookies et trackers cachés",
    "DARK WEB & ANONYMAT - Utiliser des VM pour surf anonymisé",
    "DARK WEB & ANONYMAT - Sauvegarder les clés PGP en sécurité",
    "DARK WEB & ANONYMAT - Éviter les fuites de métadonnées",
    
    # SYSTÈMES D’EXPLOITATION
    "SYSTÈMES D’EXPLOITATION - Installer Linux Ubuntu pas à pas",
    "SYSTÈMES D’EXPLOITATION - Créer une clé USB bootable",
    "SYSTÈMES D’EXPLOITATION - Partitionner un disque dur",
    "SYSTÈMES D’EXPLOITATION - Installer Windows 11",
    "SYSTÈMES D’EXPLOITATION - Découvrir les commandes Linux de base",
    "SYSTÈMES D’EXPLOITATION - Gérer les utilisateurs sous Linux",
    "SYSTÈMES D’EXPLOITATION - Mettre à jour son OS en toute sécurité",
    "SYSTÈMES D’EXPLOITATION - Installer un dual boot Windows/Linux",
    "SYSTÈMES D’EXPLOITATION - Sauvegarder son système avec Clonezilla",
    "SYSTÈMES D’EXPLOITATION - Utiliser une machine virtuelle avec VirtualBox",
    "SYSTÈMES D’EXPLOITATION - Configurer un firewall Linux",
    "SYSTÈMES D’EXPLOITATION - Installer des drivers sous Linux",
    "SYSTÈMES D’EXPLOITATION - Optimiser Windows 11 pour gaming",
    "SYSTÈMES D’EXPLOITATION - Configurer SSH pour administration distante",
    "SYSTÈMES D’EXPLOITATION - Utiliser rsync pour sauvegarde automatique",
    "SYSTÈMES D’EXPLOITATION - Gérer les paquets avec apt et yum",
    "SYSTÈMES D’EXPLOITATION - Sécuriser un serveur web",
    "SYSTÈMES D’EXPLOITATION - Créer des scripts bash automatisés",
    "SYSTÈMES D’EXPLOITATION - Utiliser cron pour tâches planifiées",
    "SYSTÈMES D’EXPLOITATION - Résoudre les problèmes de démarrage Linux",

    # INTELLIGENCE ARTIFICIELLE
    "INTELLIGENCE ARTIFICIELLE - Comprendre le fonctionnement du Machine Learning",
    "INTELLIGENCE ARTIFICIELLE - Créer un chatbot avec Python",
    "INTELLIGENCE ARTIFICIELLE - Utiliser une API d’IA pour générer du texte",
    "INTELLIGENCE ARTIFICIELLE - Découvrir la vision par ordinateur",
    "INTELLIGENCE ARTIFICIELLE - Créer un modèle de reconnaissance d’images",
    "INTELLIGENCE ARTIFICIELLE - Automatiser des tâches avec l’IA",
    "INTELLIGENCE ARTIFICIELLE - Comprendre le deep learning",
    "INTELLIGENCE ARTIFICIELLE - Tester un générateur d’images IA",
    "INTELLIGENCE ARTIFICIELLE - Utiliser GPT pour rédiger un texte",
    "INTELLIGENCE ARTIFICIELLE - Les limites et risques de l’intelligence artificielle",
    "INTELLIGENCE ARTIFICIELLE - Fine-tuning d’un modèle GPT",
    "INTELLIGENCE ARTIFICIELLE - Créer un modèle de prédiction météo",
    "INTELLIGENCE ARTIFICIELLE - Analyse d’image médicale avec IA",
    "INTELLIGENCE ARTIFICIELLE - Générer des images avec diffusion stable",
    "INTELLIGENCE ARTIFICIELLE - Détection d’objets en vidéo",
    "INTELLIGENCE ARTIFICIELLE - Traduction automatique avec réseaux neuronaux",
    "INTELLIGENCE ARTIFICIELLE - Détection de fraude financière",
    "INTELLIGENCE ARTIFICIELLE - Classification de texte avec BERT",
    "INTELLIGENCE ARTIFICIELLE - Création d’avatars IA réalistes",
    "INTELLIGENCE ARTIFICIELLE - Analyse prédictive des ventes",

    # BLOCKCHAIN ET CRYPTO
    "BLOCKCHAIN ET CRYPTO - Comprendre la technologie blockchain",
    "BLOCKCHAIN ET CRYPTO - Créer un portefeuille Bitcoin",
    "BLOCKCHAIN ET CRYPTO - Envoyer et recevoir des cryptomonnaies",
    "BLOCKCHAIN ET CRYPTO - Comprendre les NFT",
    "BLOCKCHAIN ET CRYPTO - Acheter des cryptos en toute sécurité",
    "BLOCKCHAIN ET CRYPTO - Utiliser Metamask pour interagir avec la blockchain",
    "BLOCKCHAIN ET CRYPTO - Comprendre le minage de cryptomonnaies",
    "BLOCKCHAIN ET CRYPTO - Découvrir les contrats intelligents",
    "BLOCKCHAIN ET CRYPTO - Comprendre les stablecoins",
    "BLOCKCHAIN ET CRYPTO - Les risques liés aux cryptomonnaies",
    "BLOCKCHAIN ET CRYPTO - Comprendre les forks et hard forks",
    "BLOCKCHAIN ET CRYPTO - Créer un portefeuille multisig",
    "BLOCKCHAIN ET CRYPTO - Sécuriser ses transactions crypto",
    "BLOCKCHAIN ET CRYPTO - Analyse des tendances DeFi",
    "BLOCKCHAIN ET CRYPTO - Créer un token NFT sur Ethereum",
    "BLOCKCHAIN ET CRYPTO - Comprendre les protocoles Layer 2",
    "BLOCKCHAIN ET CRYPTO - Automatiser des transactions avec scripts",
    "BLOCKCHAIN ET CRYPTO - Sécurité et audits smart contracts",
    "BLOCKCHAIN ET CRYPTO - Comprendre la tokenomics",
    "BLOCKCHAIN ET CRYPTO - Utiliser les stablecoins pour trading",

    # CYBERCRIMINALITÉ & ENQUÊTES
    "CYBERCRIMINALITÉ & ENQUÊTES - Comprendre le fonctionnement d’un ransomware",
    "CYBERCRIMINALITÉ & ENQUÊTES - Étudier un phishing réel",
    "CYBERCRIMINALITÉ & ENQUÊTES - Détecter une fraude bancaire en ligne",
    "CYBERCRIMINALITÉ & ENQUÊTES - Comprendre les botnets",
    "CYBERCRIMINALITÉ & ENQUÊTES - Identifier une attaque par cheval de Troie",
    "CYBERCRIMINALITÉ & ENQUÊTES - Décoder un malware simple",
    "CYBERCRIMINALITÉ & ENQUÊTES - Enquêter sur un domaine suspect",
    "CYBERCRIMINALITÉ & ENQUÊTES - Identifier une campagne de spam",
    "CYBERCRIMINALITÉ & ENQUÊTES - Comprendre les attaques supply chain",
    "CYBERCRIMINALITÉ & ENQUÊTES - Les forums clandestins de hackers",
    "CYBERCRIMINALITÉ & ENQUÊTES - Analyse des ransomwares modernes",
    "CYBERCRIMINALITÉ & ENQUÊTES - Identifier les phishing sophistiqués",
    "CYBERCRIMINALITÉ & ENQUÊTES - Techniques d’ingénierie sociale avancées",
    "CYBERCRIMINALITÉ & ENQUÊTES - Surveillance réseau pour enquêtes",
    "CYBERCRIMINALITÉ & ENQUÊTES - Forensic sur systèmes compromis",
    "CYBERCRIMINALITÉ & ENQUÊTES - Détecter intrusion par honeypot",
    "CYBERCRIMINALITÉ & ENQUÊTES - Analyse d’attaques DDOS",
    "CYBERCRIMINALITÉ & ENQUÊTES - Rechercher les vulnérabilités web",
    "CYBERCRIMINALITÉ & ENQUÊTES - Étudier les logiciels espions",
    "CYBERCRIMINALITÉ & ENQUÊTES - Identifier campagnes de spam avancées",

    # IOT ET OBJETS CONNECTÉS
    "IOT ET OBJETS CONNECTÉS - Sécuriser une caméra connectée",
    "IOT ET OBJETS CONNECTÉS - Installer un objet connecté en toute sécurité",
    "IOT ET OBJETS CONNECTÉS - Comprendre les risques des objets connectés",
    "IOT ET OBJETS CONNECTÉS - Piratage de voiture connectée (explication théorique)",
    "IOT ET OBJETS CONNECTÉS - Configurer une montre connectée",
    "IOT ET OBJETS CONNECTÉS - Protéger un thermostat intelligent",
    "IOT ET OBJETS CONNECTÉS - Suivi de santé et données privées",
    "IOT ET OBJETS CONNECTÉS - Détecter une intrusion via objets connectés",
    "IOT ET OBJETS CONNECTÉS - Sécuriser une maison intelligente",
    "IOT ET OBJETS CONNECTÉS - Limiter les données collectées par les objets",
    "IOT ET OBJETS CONNECTÉS - Sécuriser un réseau Wi-Fi IoT",
    "IOT ET OBJETS CONNECTÉS - Chiffrer les données des capteurs",
    "IOT ET OBJETS CONNECTÉS - Mettre à jour firmware automatiquement",
    "IOT ET OBJETS CONNECTÉS - Surveillance des logs IoT",
    "IOT ET OBJETS CONNECTÉS - Éviter la collecte excessive de données",
    "IOT ET OBJETS CONNECTÉS - Sécuriser un détecteur de fumée connecté",
    "IOT ET OBJETS CONNECTÉS - Configurer alertes intrusion",
    "IOT ET OBJETS CONNECTÉS - Détection d’anomalies IoT",
    "IOT ET OBJETS CONNECTÉS - Protection de la domotique",
    "IOT ET OBJETS CONNECTÉS - Gestion des permissions IoT",

    # 5G ET RÉSEAUX
    "5G ET RÉSEAUX - Comprendre le fonctionnement de la 5G",
    "5G ET RÉSEAUX - Les avantages et risques de la 5G",
    "5G ET RÉSEAUX - Configurer un routeur 5G",
    "5G ET RÉSEAUX - Comparaison entre 4G et 5G",
    "5G ET RÉSEAUX - Sécurité des réseaux mobiles",
    "5G ET RÉSEAUX - L’impact de la 5G sur les objets connectés",
    "5G ET RÉSEAUX - Optimiser son réseau domestique",
    "5G ET RÉSEAUX - Utiliser la 5G pour le gaming",
    "5G ET RÉSEAUX - Tester la vitesse de son réseau",
    "5G ET RÉSEAUX - Déployer un petit réseau 5G privé",
    "5G ET RÉSEAUX - Sécuriser les communications critiques",
    "5G ET RÉSEAUX - Analyse des paquets réseau",
    "5G ET RÉSEAUX - Déploiement réseau privé pour entreprise",
    "5G ET RÉSEAUX - Mesurer les performances réseau",
    "5G ET RÉSEAUX - Comparer les technologies LTE et 5G",
    "5G ET RÉSEAUX - Étudier les antennes et propagation",
    "5G ET RÉSEAUX - Tester la latence et jitter",
    "5G ET RÉSEAUX - Détecter les interférences IoT",
    "5G ET RÉSEAUX - Optimisation QoS pour vidéo et streaming",
    "5G ET RÉSEAUX - Futur de la 6G et innovations"

     # PENTEST ET HACKING ÉTHIQUE
    "PENTEST - Introduction au hacking éthique",
    "PENTEST - Scanner un réseau avec Nmap",
    "PENTEST - Exploiter les vulnérabilités avec Metasploit",
    "PENTEST - Analyse de paquets avec Wireshark",
    "PENTEST - Test d’intrusion sur applications web",
    "PENTEST - Créer un lab de test virtuel",
    "PENTEST - Techniques d’escalade de privilèges",
    "PENTEST - Utiliser Burp Suite pour tester la sécurité",
    "PENTEST - Détection et contournement de firewall",
    "PENTEST - Social engineering et sécurité humaine",

    # PROGRAMMATION AVANCÉE
    "PROGRAMMATION - Introduction à Python avancé",
    "PROGRAMMATION - Programmation orientée objet en Java",
    "PROGRAMMATION - Créer des scripts automatisés en Bash",
    "PROGRAMMATION - Développement web fullstack (HTML/CSS/JS)",
    "PROGRAMMATION - Frameworks React et Vue.js",
    "PROGRAMMATION - Développement d’API REST avec Python",
    "PROGRAMMATION - Débogage et optimisation de code",
    "PROGRAMMATION - Gestion de bases de données SQL",
    "PROGRAMMATION - Développement de jeux vidéo avec Unity",
    "PROGRAMMATION - Introduction au Rust et sécurité mémoire",

    # RÉSEAUX & SÉCURITÉ
    "RÉSEAUX - Comprendre le modèle OSI",
    "RÉSEAUX - Configuration d’un routeur Cisco",
    "RÉSEAUX - VPN et tunnels sécurisés",
    "RÉSEAUX - Détection d’intrusions avec Snort",
    "RÉSEAUX - Analyse de logs réseau",
    "RÉSEAUX - Sécuriser un serveur DNS",
    "RÉSEAUX - Protection contre DDoS",
    "RÉSEAUX - Surveillance réseau avec Nagios",
    "RÉSEAUX - Configurer un proxy transparent",
    "RÉSEAUX - Détection de vulnérabilités réseau",

    # CLOUD & INFRASTRUCTURE
    "CLOUD - Introduction à AWS",
    "CLOUD - Déployer un serveur web sur Azure",
    "CLOUD - Sécuriser des instances EC2",
    "CLOUD - Gestion des permissions IAM",
    "CLOUD - Stockage sécurisé avec S3",
    "CLOUD - Mise en place de CI/CD",
    "CLOUD - Supervision et monitoring des services",
    "CLOUD - Conteneurs Docker et Kubernetes",
    "CLOUD - Automatisation avec Terraform",
    "CLOUD - Haute disponibilité et tolérance aux pannes",

    # DATA & ANALYTICS
    "DATA - Introduction au Big Data",
    "DATA - Manipulation de données avec Python Pandas",
    "DATA - Visualisation avec Matplotlib et Seaborn",
    "DATA - Analyse prédictive avec Scikit-learn",
    "DATA - Bases de données NoSQL (MongoDB)",
    "DATA - Création de dashboards avec PowerBI",
    "DATA - Traitement de données en temps réel",
    "DATA - Analyse de logs pour la sécurité",
    "DATA - Machine Learning appliqué au e-commerce",
    "DATA - Modélisation statistique avancée",

    # INTERNET DES OBJETS & AUTOMATISATION
    "IOT - Créer un capteur connecté avec Arduino",
    "IOT - Sécuriser un réseau domotique",
    "IOT - Automatiser des tâches avec Raspberry Pi",
    "IOT - Collecte et analyse de données IoT",
    "IOT - Surveillance de l’énergie domestique",
    "IOT - Communication MQTT sécurisée",
    "IOT - Détection d’anomalies et alertes",
    "IOT - Déploiement IoT à grande échelle",
    "IOT - Optimisation de la consommation énergétique",
    "IOT - Maintenance et mise à jour sécurisée",

    # CRYPTO & FINANCE
    "CRYPTO - Stratégies de trading crypto",
    "CRYPTO - Analyse technique sur cryptos",
    "CRYPTO - Sécurisation d’exchanges",
    "CRYPTO - Smart contracts Ethereum avancés",
    "CRYPTO - Audit de smart contracts",
    "CRYPTO - Défi DeFi et yield farming",
    "CRYPTO - Sécurité des wallets hardware",
    "CRYPTO - Comprendre les stablecoins et pegged assets",
    "CRYPTO - Gestion de portefeuilles diversifiés",
    "CRYPTO - Légalité et régulations crypto",

    # IA & AUTOMATISATION
    "IA - Automatiser la génération de contenus",
    "IA - Création de modèles NLP personnalisés",
    "IA - IA générative pour images et vidéos",
    "IA - Chatbots conversationnels avancés",
    "IA - Analyse de sentiment et prédiction",
    "IA - IA pour la cybersécurité",
    "IA - IA pour la finance et trading",
    "IA - Optimisation de processus avec IA",
    "IA - Reconnaissance faciale et éthique",
    "IA - Détection de deepfake et fraude",

    # CYBERCRIMINALITÉ & FORENSIC
    "FORENSIC - Analyse de systèmes compromis",
    "FORENSIC - Récupération de fichiers supprimés",
    "FORENSIC - Étude de logs pour enquêtes",
    "FORENSIC - Analyse de malware avancé",
    "FORENSIC - Techniques de reverse engineering",
    "FORENSIC - Étude de ransomwares récents",
    "FORENSIC - Capture et analyse de paquets",
    "FORENSIC - Forensic cloud et virtualisation",
    "FORENSIC - Audit sécurité web",
    "FORENSIC - Analyse réseau pour intrusions",

    # NOUVELLES TECHNOLOGIES
    "TECH - Blockchain avancée et applications",
    "TECH - Réalité augmentée et VR",
    "TECH - Impression 3D et applications industrielles",
    "TECH - Robotique et IA",
    "TECH - Edge computing et IoT",
    "TECH - Quantum computing introduction",
    "TECH - Technologies vertes et énergie renouvelable",
    "TECH - Smart cities et capteurs intelligents",
    "TECH - Voitures autonomes et sécurité",
    "TECH - Futur des communications satellites",

        # JEUX VIDÉO & CYBERSÉCURITÉ GAMING
    "GAMING - Sécuriser son compte Steam",
    "GAMING - Prévenir les cheat et hacks en ligne",
    "GAMING - Analyse des vulnérabilités des serveurs de jeux",
    "GAMING - Sécurité des microtransactions",
    "GAMING - Protection des données personnelles en jeu",
    "GAMING - Optimisation réseau pour gaming compétitif",
    "GAMING - Détection de triche via anti-cheat",
    "GAMING - Modding et risques de sécurité",
    "GAMING - Créer son serveur de jeu sécurisé",
    "GAMING - Analyse de malware lié aux jeux",

    # RÉALITÉ VIRTUELLE & AUGMENTÉE
    "VR/AR - Introduction à la VR/AR",
    "VR/AR - Développement d’applications VR avec Unity",
    "VR/AR - Sécurité et vie privée en VR",
    "VR/AR - ARKit et ARCore pour débutants",
    "VR/AR - Optimisation de performance VR",
    "VR/AR - Création d’expériences immersives",
    "VR/AR - Tracking et interactions utilisateurs",
    "VR/AR - Débogage et tests VR/AR",
    "VR/AR - Développement multi-plateformes VR/AR",
    "VR/AR - Futur de la réalité mixte",

    # ÉLECTRONIQUE & HACKING HARDWARE
    "HARDWARE - Introduction au hacking hardware",
    "HARDWARE - Analyse des circuits électroniques",
    "HARDWARE - Microcontrôleurs et sécurité",
    "HARDWARE - Reverse engineering de PCB",
    "HARDWARE - Piratage de cartes RFID/NFC",
    "HARDWARE - Attaques sur IoT et capteurs",
    "HARDWARE - Sécurisation d’appareils embarqués",
    "HARDWARE - Techniques de soldering et prototyping",
    "HARDWARE - Logic analyzers pour hacking",
    "HARDWARE - Détection de malwares hardware",

    # ETHICAL AI & INTELLIGENCE ARTIFICIELLE RESPONSABLE
    "ETHICAL_AI - Principes d’IA responsable",
    "ETHICAL_AI - Biais et fairness dans les modèles",
    "ETHICAL_AI - Protection de la vie privée avec IA",
    "ETHICAL_AI - IA explicable et interprétable",
    "ETHICAL_AI - IA et réglementation",
    "ETHICAL_AI - Sécuriser les modèles ML",
    "ETHICAL_AI - Prévention des deepfakes malveillants",
    "ETHICAL_AI - IA pour la cybersécurité",
    "ETHICAL_AI - IA pour la santé et bioéthique",
    "ETHICAL_AI - Détection des modèles biaisés",

    # FUTUR DES TECH & INNOVATION
    "FUTUR_TECH - Quantum computing et applications",
    "FUTUR_TECH - Edge computing et IoT avancé",
    "FUTUR_TECH - Smart cities et infrastructures intelligentes",
    "FUTUR_TECH - Technologies spatiales et satellites",
    "FUTUR_TECH - Véhicules autonomes et sécurité",
    "FUTUR_TECH - Energies renouvelables et tech verte",
    "FUTUR_TECH - Robotique avancée et IA",
    "FUTUR_TECH - Nanotechnologies et applications",
    "FUTUR_TECH - Biotechnologie et santé connectée",
    "FUTUR_TECH - Innovations dans la blockchain",

    # ÉDUCATION & FORMATION EN LIGNE
    "EDUCATION - Créer un cours en ligne",
    "EDUCATION - Plateformes e-learning et LMS",
    "EDUCATION - Sécurité des données des étudiants",
    "EDUCATION - Gamification et engagement",
    "EDUCATION - Analyse des performances d’apprentissage",
    "EDUCATION - Automatisation des évaluations",
    "EDUCATION - Création de vidéos éducatives",
    "EDUCATION - Outils collaboratifs pour l’enseignement",
    "EDUCATION - IA pour l’éducation personnalisée",
    "EDUCATION - Éducation sur la cybersécurité",

    # MÉTAVERSE & WEB3
    "WEB3 - Introduction au Web3 et décentralisation",
    "WEB3 - Créer un NFT sur Ethereum",
    "WEB3 - Développer un DApp sécurisé",
    "WEB3 - Smart contracts et audit",
    "WEB3 - DAO et gouvernance décentralisée",
    "WEB3 - Tokenomics et cryptomonnaies",
    "WEB3 - Interaction avec la blockchain via API",
    "WEB3 - Sécuriser son portefeuille Web3",
    "WEB3 - Gaming et NFT",
    "WEB3 - Futur du Web décentralisé",

    # CYBERSÉCURITÉ AVANCÉE
"CYBERSEC - Pentesting avancé avec Metasploit",
"CYBERSEC - Exploitation de vulnérabilités web",
"CYBERSEC - Attaques et défense réseau",
"CYBERSEC - Sécuriser les serveurs Linux",
"CYBERSEC - Analyse forensique d’un incident",
"CYBERSEC - Détection et mitigation DDoS",
"CYBERSEC - Reverse engineering de malware",
"CYBERSEC - Sécurité des applications mobiles",
"CYBERSEC - Hacking de protocoles IoT",
"CYBERSEC - Bug bounty et rapport de vulnérabilité",

# CLOUD & INFRASTRUCTURE
"CLOUD - Introduction à AWS, Azure, GCP",
"CLOUD - Sécuriser un serveur cloud",
"CLOUD - Déploiement d’application scalable",
"CLOUD - Infrastructure as Code avec Terraform",
"CLOUD - Monitoring et logging cloud",
"CLOUD - Conteneurisation avec Docker",
"CLOUD - Orchestration avec Kubernetes",
"CLOUD - Sauvegarde et reprise après sinistre",
"CLOUD - Réseaux virtuels et VPN",
"CLOUD - Automatisation des tâches cloud",

# DATA SCIENCE & ANALYTICS
"DATA - Introduction au Data Science",
"DATA - Nettoyage et préparation de données",
"DATA - Visualisation de données avec Python",
"DATA - Analyse statistique avancée",
"DATA - Machine Learning pour prédictions",
"DATA - NLP et traitement du langage",
"DATA - Big Data et Spark",
"DATA - Analyse de séries temporelles",
"DATA - Détection d’anomalies",
"DATA - Déploiement de modèles ML en production",

# DÉVELOPPEMENT WEB & MOBILE
"WEB - HTML et CSS pour débutants",
"WEB - JavaScript avancé",
"WEB - Frameworks front-end (React, Vue, Angular)",
"WEB - Développement back-end avec Node.js",
"WEB - Sécuriser une application web",
"WEB - API REST et GraphQL",
"WEB - Déploiement web sécurisé",
"WEB - Applications mobiles avec Flutter",
"WEB - Optimisation performance web",
"WEB - Progressive Web Apps (PWA)",

# RÉSEAUX & TELECOM
"NETWORK - Concepts TCP/IP et modèles OSI",
"NETWORK - Sécuriser un réseau WiFi",
"NETWORK - VPN et chiffrement réseau",
"NETWORK - Analyse de trafic avec Wireshark",
"NETWORK - Routage et switching avancé",
"NETWORK - Détection d’intrusion IDS/IPS",
"NETWORK - Protocoles réseau sécurisés",
"NETWORK - Monitoring réseau avec Nagios",
"NETWORK - Troubleshooting réseau",
"NETWORK - Réseaux privés et segmentation",

# PRIVACY & PROTECTION DES DONNÉES
"PRIVACY - Gestion des mots de passe sécurisés",
"PRIVACY - Chiffrement des emails",
"PRIVACY - VPN et proxy avancé",
"PRIVACY - Anonymisation des données",
"PRIVACY - Sécuriser ses communications en ligne",
"PRIVACY - Vie privée sur les réseaux sociaux",
"PRIVACY - Protection contre le tracking web",
"PRIVACY - Sécurité des appareils mobiles",
"PRIVACY - Stockage sécurisé des données",
"PRIVACY - Audit de confidentialité personnel",

# BIOTECH & SCIENCES
"BIOTECH - Introduction à la biotechnologie",
"BIOTECH - Édition génétique CRISPR",
"BIOTECH - Bioinformatique pour débutants",
"BIOTECH - Sécurité et éthique en biotech",
"BIOTECH - Capteurs biomédicaux connectés",
"BIOTECH - Analyse de séquences ADN",
"BIOTECH - Modélisation biologique",
"BIOTECH - Robotique et biotechnologie",
"BIOTECH - Nanobiotechnologies",
"BIOTECH - Intelligence artificielle appliquée à la santé",
]

# ---------------- HISTORY HANDLING ----------------
def ensure_history_path(path: str):
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

def load_history(path: str):
    ensure_history_path(path)
    if not os.path.exists(path):
        history = {
            "titles": [],
            "days": {},
            "cat_index": 0,
            "category_loops": {},
            "recent_articles": {}
        }
        return history
    try:
        history = json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        history = {
            "titles": [],
            "days": {},
            "cat_index": 0,
            "category_loops": {},
            "recent_articles": {}
        }

    # --- AUTO-INITIALIZE MISSING FIELDS ---
    history.setdefault("titles", [])
    history.setdefault("days", {})
    history.setdefault("cat_index", 0)
    history.setdefault("category_loops", {})
    history.setdefault("recent_articles", {})

    # --- ENSURE ALL CATEGORIES HAVE entries ---
    for cat in CATEGORIES:
        if cat not in history["category_loops"]:
            history["category_loops"][cat] = 0
        if cat not in history["recent_articles"]:
            history["recent_articles"][cat] = []

    return history

def save_history(path: str, data: dict):
    ensure_history_path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def title_in_history(title: str, history: dict) -> bool:
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()
    return h in history.get("titles", [])

def add_title_to_history(title: str, history: dict):
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()
    if "titles" not in history:
        history["titles"] = []
    if h not in history["titles"]:
        history["titles"].append(h)

# ---------------- MAIL ----------------
def mail_post(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = BLOGGER_MAIL
    msg.attach(MIMEText(html_body, "html"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, BLOGGER_MAIL, msg.as_string())

# ---------------- AI PROMPTS ----------------
def gen_punchy_title_and_meta(category: str, loop_index: int = 0, recent_titles: list = None):
    recent_text = ""
    if recent_titles:
        recent_text = "Évite les angles, formulations ou titres déjà utilisés récemment:\n" + \
                      "\n".join(f"- {t}" for t in recent_titles)

    prompt = f"""
Tu es un rédacteur SEO en 2025. Crée pour la catégorie suivante un SEUL titre
percutant et “clickbait” en français (max 70 caractères), commençant par UN seul emoji.
Puis une méta description unique, fait en sorte qu'il ne deborde pas (max 150 caractères).

Catégorie: {category}
C'est la {loop_index+1}ᵉ fois que nous écrivons sur cette catégorie.
{recent_text}

Renvoie STRICTEMENT au format JSON:
{{"title": "...", "meta": "..."}}
"""
    model = genai.GenerativeModel(MODEL)
    out = model.generate_content(prompt).text.strip()
    import re, json as pyjson
    m = re.search(r'\{.*\}', out, re.S)
    if not m:
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")
    try:
        data = pyjson.loads(m.group(0))
        title = data.get("title","").strip().strip('"')
        meta  = data.get("meta","").strip()[:150]
        if not title:
            title = "✨ " + category.split("–")[0].strip()
        return title, meta
    except Exception:
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")

def gen_full_article_html(category: str, title: str, meta_desc: str, loop_index: int = 0):
    prompt = f"""
Rédige un article bien structuré de blog en FRANÇAIS pour Blogger compatible avec l'éditeur de Blogger (HTML uniquement, sans <html> ni <body>).

Contexte:
- Catégorie: {category}
- Titre: {title}
- Meta description: {meta_desc}
- C'est la {loop_index+1}ᵉ fois que nous écrivons sur cette catégorie,
  propose un angle DIFFÉRENT des fois précédentes et un contenu UNIQUE.

Exigences SEO & mise en forme:
- Longueur: 800–1200 mots
- Première ligne EXACTE: <p class='meta'>{meta_desc}</p>
- Titre H1: <h1>{title}</h1>
- TOC ancré: <nav id='toc'> avec liens vers CHAQUE H2 (ancres id)
- Structure: H2 (sections), H3 (sous-sections)
- Laisse une LIGNE BLANCHE entre chaque titre et chaque paragraphe
- Utilise des listes à puces (ul/li) quand pertinent
- Mets en valeur les mots importants/clés avec <strong>, <em>, et du monospace <code> pour commandes/extraits
- pas de *mot* ni de code Markdown
- Ajoute quelques touches de couleur pertinentes via <span style="color:#2363eb">…</span>
- Ajoute 1–2 encadrés “conseil/alerte” avec <blockquote class="tip"> et <blockquote class="warning"> 
- Ajoute un CTA final (inscription newsletter / partage / commentaire)
- Pas d’images externes dans cet article
- Pas d’auto-promo, pas de répétition inutile
- Français naturel, ton professionnel et pédagogique
- Vérifie toujour que chaque article respect la structure SEO
"""
    model = genai.GenerativeModel(MODEL)
    html = model.generate_content(prompt).text.strip()
    if html.startswith("```html"):
        html = html[7:]
    if html.endswith("```"):
        html = html[:-3]
    return html

# ---------------- CATEGORY PICKING ----------------
def pick_sequential_categories(history: dict, k: int) -> list:
    today_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    posted_today = set(history.get("days", {}).get(today_key, []))
    start_idx = history.get("cat_index", 0)
    chosen = []

    i = 0
    while len(chosen) < k:
        idx = (start_idx + i) % len(CATEGORIES)
        cat = CATEGORIES[idx]
        if cat not in posted_today:
            chosen.append(cat)
        i += 1
        if i > len(CATEGORIES) * 2:  # safety break
            break

    history["cat_index"] = (start_idx + i) % len(CATEGORIES)
    return chosen

# ---------------- MAIN ----------------
def main():
    today_utc = datetime.now(timezone.utc)
    today_key = today_utc.strftime("%Y-%m-%d")

    history = load_history(HISTORY_FILE)
    history.setdefault("days", {})
    history.setdefault("cat_index", 0)
    history.setdefault("category_loops", {})
    history.setdefault("recent_articles", {})

    chosen = pick_sequential_categories(history, ARTICLES_PER_DAY)
    posted_today = []

    for category in chosen:
        loop_index = history["category_loops"].get(category, 0)
        recent_titles = history["recent_articles"].get(category, [])[-7:]

        title, meta = gen_punchy_title_and_meta(category, loop_index, recent_titles)
        tries = 0
        while title_in_history(title, history) and tries < MAX_RETRIES_TITLE:
            tries += 1
            title, meta = gen_punchy_title_and_meta(category, loop_index, recent_titles)
        if title_in_history(title, history):
            print(f"[SKIP] Titre déjà utilisé pour '{category}': {title}")
            continue

        html = gen_full_article_html(category, title, meta, loop_index)
        mail_post(title, html)
        add_title_to_history(title, history)
        posted_today.append(category)

        # update loop index
        history["category_loops"][category] = loop_index + 1

        # update recent_articles
        history.setdefault("recent_articles", {})
        history.setdefault("recent_articles", {}).setdefault(category, [])
        history["recent_articles"][category].append(title)
        # keep last 7 articles
        history["recent_articles"][category] = history["recent_articles"][category][-7:]

        print(f"[OK] Publié: {title} ({category}, loop {loop_index+1})")

    history["days"][today_key] = posted_today
    save_history(HISTORY_FILE, history)

if __name__ == "__main__":
    main()
