# Fix pour Git Push - Authentification GitHub

## Problème Identifié
Git demande l'authentification mais ne peut pas lire les credentials depuis le terminal.

## Solutions

### Solution 1: Utiliser un Personal Access Token (Recommandé)

1. **Créer un token GitHub** :
   - Allez sur: https://github.com/settings/tokens
   - Cliquez "Generate new token" → "Generate new token (classic)"
   - Donnez-lui un nom (ex: "API Key Finder")
   - Sélectionnez les permissions: `repo` (toutes)
   - Cliquez "Generate token"
   - **COPIEZ LE TOKEN** (vous ne le verrez qu'une fois!)

2. **Utiliser le token lors du push** :
```bash
# Quand Git demande le username, entrez votre nom d'utilisateur GitHub
# Quand Git demande le password, collez le TOKEN (pas votre mot de passe)
git push
```

3. **Sauvegarder le token dans le keychain macOS** :
```bash
# Le token sera sauvegardé automatiquement dans le keychain macOS
# Vous n'aurez plus à le ressaisir
```

### Solution 2: Configurer GitHub CLI (Plus Simple)

```bash
# Installer GitHub CLI
brew install gh

# S'authentifier
gh auth login

# Choisir:
# - GitHub.com
# - HTTPS
# - Authenticate Git with your GitHub credentials? Yes
# - Login with a web browser

# Puis push
git push
```

### Solution 3: Utiliser SSH (Si vous avez une clé SSH)

```bash
# Générer une clé SSH si vous n'en avez pas
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copier la clé publique
cat ~/.ssh/id_ed25519.pub | pbcopy

# Ajouter la clé sur GitHub:
# https://github.com/settings/keys
# New SSH key → Coller la clé → Add SSH key

# Changer le remote pour SSH
git remote set-url origin git@github.com:airhick/apifinder.git

# Push
git push
```

### Solution 4: Utiliser le token directement dans l'URL (Temporaire)

```bash
# Remplacer USERNAME et TOKEN
git remote set-url origin https://USERNAME:TOKEN@github.com/airhick/apifinder.git

# Push
git push

# ⚠️ ATTENTION: Cette méthode expose le token dans l'historique git
# Ne l'utilisez que temporairement, puis changez le remote
```

## Solution Rapide Recommandée

**Option la plus simple** : Utiliser GitHub CLI

```bash
# Installer GitHub CLI
brew install gh

# S'authentifier (ouvrira le navigateur)
gh auth login

# Push
git push
```

C'est la méthode la plus simple et sécurisée !

