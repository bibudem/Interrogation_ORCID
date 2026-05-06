# ORCID Explorer

Interface web pour explorer l'API publique ORCID. Développée en Python/Flask, elle permet de consulter des profils de chercheurs, d'effectuer des recherches avancées et d'exporter des données — notamment pour identifier les chercheurs affiliés à une institution comme l'Université de Montréal.

Compatible **Windows** et **macOS**.

---

## Table des matières

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Lancement](#lancement)
- [Fonctionnalités](#fonctionnalités)
- [Structure du projet](#structure-du-projet)
- [Endpoints disponibles](#endpoints-disponibles)
- [Notes sur les données ORCID](#notes-sur-les-données-orcid)
- [Passer en production](#passer-en-production)

---

## Prérequis

- **Python 3.10 ou plus récent**
  - Windows : [python.org](https://www.python.org/downloads/) — cocher **« Add Python to PATH »** lors de l'installation
  - macOS : [python.org](https://www.python.org/downloads/) ou via Homebrew : `brew install python`
- Connexion internet (pour joindre l'API ORCID)

---

## Installation

### Windows

```powershell
Expand-Archive -Path orcid-app.zip -DestinationPath . -Force
cd orcid-app
.\installer.ps1
```

> **En cas d'erreur « l'exécution de scripts est désactivée »**, exécuter d'abord :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### macOS

```bash
unzip orcid-app.zip
cd orcid-app
chmod +x installer.sh
./installer.sh
```

---

Le script d'installation effectue automatiquement les étapes suivantes :

1. Vérifie que Python est disponible
2. Crée un environnement virtuel Python (`.venv`)
3. Installe les dépendances (Flask, requests)
4. Lance l'application

> **Note technique :** les scripts appellent directement les exécutables du venv
> (`.venv/bin/python` sur Mac, `.venv\Scripts\python.exe` sur Windows) plutôt que
> de passer par l'activation du venv. Cela évite les problèmes de politique
> d'exécution et garantit que les bonnes dépendances sont utilisées.

---

## Lancement

Après la première installation, utiliser le script de lancement rapide.

### Windows

```powershell
cd orcid-app
.\lancer.ps1
```

### macOS

```bash
cd orcid-app
./lancer.sh
```

L'application sera disponible sur **http://localhost:5000**

Pour arrêter : **Ctrl+C** dans le terminal.

---

## Fonctionnalités

### Sélection d'environnement

Un sélecteur dans la barre de navigation permet de basculer entre :

| Environnement | URL API | Usage |
|---|---|---|
| **Sandbox** | `pub.sandbox.orcid.org/v3.0` | Tests — données fictives |
| **Production** | `pub.orcid.org/v3.0` | Données réelles |

L'environnement actif est mémorisé pour toute la session de navigation.

---

### Page Profil chercheur

Affiche toutes les données publiques d'un profil ORCID à partir de son identifiant (`0000-0000-0000-000X`). L'URL complète (`https://orcid.org/0000-...`) est également acceptée.

**Données d'identification affichées :**

| Section | Données |
|---|---|
| Identité | Nom complet, prénom, nom de famille, autres noms/variantes, crédit name |
| Contact | Courriels (avec indicateurs « principal » et « vérifié »), pays/adresses |
| Identifiants externes | Scopus Author ID, ResearcherID (Clarivate), Loop ID, ISNI, etc. |
| Présence en ligne | Sites web, Google Scholar, ResearchGate, pages personnelles |
| Biographie | Texte libre de présentation |
| Mots-clés | Domaines de recherche déclarés |

**Parcours professionnel :**

| Section | Données |
|---|---|
| Emplois & affiliations | Organisation, département, rôle, années, identifiant ROR/Ringgold/GRID |
| Formation académique | Établissement, diplôme/grade, département, années |
| Financements | Titre, organisme subventionnaire, type, années |
| Publications | Titre, revue, DOI cliquable, type, année (tri décroissant) |

**Exports disponibles depuis le profil :**

- **JSON complet** — télécharge `orcid_{id}.json` contenant :
  - Les données extraites et structurées (`profile`)
  - La réponse brute complète de l'API ORCID (`raw_orcid_record`)
  - Des métadonnées d'export (environnement, date, version API)
- **JSON brut ORCID** — ouvre la réponse brute de l'API dans le navigateur

---

### Page Recherche

Permet de trouver des chercheurs en combinant plusieurs critères. Utilise la syntaxe Solr de l'API ORCID.

**Critères disponibles :**

| Champ | Champ Solr correspondant | Exemple |
|---|---|---|
| Nom de famille | `family-name` | `Dupont` |
| Prénom | `given-names` | `Marie` |
| Institution | `affiliation-org-name` | `Université de Montréal` |
| Mot-clé | `keyword` | `bibliométrie` |
| Courriel ou domaine | `email` | `*@umontreal.ca` |
| Identifiant ORCID | `orcid` | `0000-0002-1825-0097` |
| Requête Solr libre | *(directe)* | `doi-self:10.1000/xyz` |

Les critères sont combinés avec `AND`. Depuis les résultats, chaque profil peut être chargé directement dans la page Profil.

**Export UdeM :** le bouton **CSV @umontreal.ca** déclenche une extraction complète de tous les profils ORCID dont le courriel public se termine par `@umontreal.ca`. Le fichier CSV généré contient : ORCID ID, URL, nom complet, prénom, nom de famille, courriels, autres noms, pays, identifiants externes, sites web, affiliations, formations et nombre de publications.

> Ce processus peut prendre plusieurs minutes selon le nombre de profils trouvés, car l'application pagine automatiquement et respecte un délai entre les appels pour ne pas surcharger l'API.

---

## Structure du projet

```
orcid-app/
├── app.py                  # Application Flask — logique principale
├── requirements.txt        # Dependances Python (flask, requests)
├── installer.ps1           # Script d'installation Windows
├── lancer.ps1              # Script de lancement rapide Windows
├── installer.sh            # Script d'installation macOS
├── lancer.sh               # Script de lancement rapide macOS
├── README.md               # Ce fichier
└── templates/
    ├── base.html           # Layout commun (nav, styles, sélecteur d'environnement)
    ├── index.html          # Page d'accueil
    ├── profil.html         # Page profil chercheur
    └── recherche.html      # Page recherche + export CSV UdeM
```

### Architecture de `app.py`

Le code est organisé en quatre couches :

1. **Configuration** — définition des environnements (sandbox/production), headers HTTP
2. **`OrcidClient`** — classe qui encapsule tous les appels HTTP vers l'API ORCID, incluant la pagination automatique via `search_all()`
3. **Helpers `extract_*`** — fonctions de transformation des réponses JSON brutes en structures Python propres
4. **Routes Flask** — `/`, `/profil`, `/recherche`, `/set-env`, `/export-umontreal`, `/profil/<id>/export-json`, `/api/profil/<id>`

---

## Endpoints disponibles

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/` | Page d'accueil |
| `GET/POST` | `/profil` | Affichage du profil chercheur |
| `GET` | `/profil/{id}/export-json` | Téléchargement JSON du profil complet |
| `GET/POST` | `/recherche` | Recherche de chercheurs |
| `GET` | `/export-umontreal` | Export CSV @umontreal.ca |
| `POST` | `/set-env` | Basculer sandbox ↔ production |
| `GET` | `/api/profil/{id}` | JSON brut ORCID (débogage) |

---

## Notes sur les données ORCID

**Données publiques seulement** — cette application utilise l'API publique ORCID, qui ne retourne que les données que le chercheur a explicitement rendues publiques dans son profil. Les courriels, adresses et identifiants marqués *limited* ou *private* ne sont pas accessibles.

**Photo de profil** — ORCID ne l'expose pas via l'API publique. Elle est accessible uniquement via OAuth avec le consentement explicite du chercheur (Member API).

**Courriels institutionnels** — un chercheur peut avoir un courriel `@umontreal.ca` dans son profil ORCID sans l'avoir rendu public. L'export CSV UdeM ne récupère donc que les profils avec un courriel public correspondant au domaine, ce qui peut sous-représenter l'ensemble des chercheurs affiliés.

**Profil de démonstration** — l'identifiant `0000-0002-1825-0097` est le profil officiel de démonstration ORCID, disponible dans les deux environnements.

---

## Passer en production

L'environnement se change directement depuis l'interface (bouton dans la barre de navigation). Aucune modification de code n'est nécessaire.

Pour forcer l'environnement de démarrage par défaut, modifier cette ligne dans `app.py` :

```python
# Remplacer "sandbox" par "production"
return session.get("env", "sandbox")
```

---

## Dépendances

| Paquet | Version minimale | Usage |
|---|---|---|
| `flask` | 3.0.0 | Serveur web et rendu des templates |
| `requests` | 2.31.0 | Appels HTTP vers l'API ORCID |

---

*ORCID Explorer — API ORCID v3.0 — Interface publique (sans authentification)*
