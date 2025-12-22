# Fix pour Git Push Lent

## Solution Immédiate

### 1. Annuler le push actuel
Appuyez sur **Ctrl+C** dans le terminal pour annuler le push en cours.

### 2. Vérifier la connexion
```bash
# Tester la connexion à GitHub
ping github.com

# Vérifier votre configuration git
git remote -v
```

### 3. Essayer avec verbose pour voir ce qui se passe
```bash
git push --verbose
```

### 4. Si toujours lent, essayer avec compression désactivée
```bash
git push --no-verify
```

### 5. Alternative : Push avec timeout
```bash
# Push avec timeout de 30 secondes
timeout 30 git push || echo "Push timeout"
```

## Solutions à Long Terme

### Option A: Push en arrière-plan avec nohup
```bash
nohup git push > push.log 2>&1 &
# Vérifier le log
tail -f push.log
```

### Option B: Utiliser SSH au lieu de HTTPS
```bash
# Vérifier votre remote
git remote get-url origin

# Si c'est HTTPS, changer pour SSH
git remote set-url origin git@github.com:USERNAME/REPO.git
```

### Option C: Augmenter le buffer git
```bash
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999
```

### Option D: Utiliser un proxy si nécessaire
```bash
# Si vous êtes derrière un proxy
git config --global http.proxy http://proxy.example.com:8080
```

## Vérifier ce qui bloque

```bash
# Voir les processus git
ps aux | grep git

# Voir la taille des objets à pousser
git count-objects -vH

# Voir ce qui sera poussé
git log origin/main..HEAD --oneline
```

## Solution Rapide Recommandée

1. **Ctrl+C** pour annuler
2. Vérifier: `git remote -v`
3. Essayer: `git push --verbose` pour voir où ça bloque
4. Si HTTPS, passer à SSH: `git remote set-url origin git@github.com:USERNAME/REPO.git`

