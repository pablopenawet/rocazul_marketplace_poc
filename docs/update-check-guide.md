# Update Check Guide

> Procedimiento de referencia para `/update-check` en rocazul-marketplace-poc. Adaptado de [dev-forge](https://github.com/dmedina-dev/dev-forge) (`plugins/forge-keeper/skills/forge-keeper/references/update-check-guide.md`). Úsalo cuando ejecutes un update check, revises cambios upstream, o apliques un merge.

Este documento describe el algoritmo completo del slash command `/update-check` (ubicado en `.claude/commands/update-check.md`). El comando es thin y referencia este guide para la ejecución detallada.

---

## Plugin Scanning

Escanea cada directorio de plugin para encontrar los que tienen sources upstream que comprobar.

### Steps

1. Listar todos los plugins: `plugins/*/.claude-plugin/customizations.json`
2. Para cada archivo encontrado, leer y clasificar el plugin:

**Single-origin plugins** (clave `origin`, singular) — es el caso por defecto en rocazul:
```json
{ "origin": { "type": "github", "repo": "jvillar/claude-plugins", "path": "plugins/bash-guard", "ref": "main", ... } }
```

**Multi-origin plugins** (clave `origins`, array) — no usado actualmente en rocazul, pero soportado por compatibilidad con dev-forge:
```json
{ "origins": [ { "repo": "owner/repo-a", "path": "x", "ref": "main" }, { "repo": "owner/repo-b", "path": "y", "ref": "v1.0.0" } ] }
```

### Skip rules

- Plugins **sin** `customizations.json` → nativos de rocazul, no tienen upstream. Skip.
- Si `origin.type` fuera `"native"`, skip (en rocazul no usamos ese marcador — la ausencia de `customizations.json` cumple la misma función).
- Si `origins` array contiene una entry con `type: "native"`, skip sólo esa entry.

### Collected data per plugin

Para cada plugin no-skipped, registrar:
- Nombre del plugin (nombre del directorio bajo `plugins/`)
- Path del customizations.json
- Origin(s): repo, path (puede ser string vacío), ref actual, fetched_at, commit actual
- Lista de customizations: id, type, target, summary, reason
- Si es single-origin o multi-origin
- Ancestry (opcional, sólo contexto — no participa en update check)

---

## Upstream Check

Determinar si existen versiones más nuevas para cada origin.

### Tag-style refs (e.g., v5.0.6)

Un ref que empieza con `v` seguido de número de versión es tag-style.

**Primary method — GitHub releases API:**
```bash
gh api repos/{owner}/{repo}/releases/latest --jq '{tag: .tag_name, published: .published_at, body: .body}'
```

**Fallback — git ls-remote:**
```bash
git ls-remote --tags https://github.com/{owner}/{repo}.git 'refs/tags/v*'
```
Parsear output, strip `refs/tags/`, picar el highest semver tag.

**¿Hay updates?** Comparar `ref` actual contra latest tag con semver ordering. Si latest > current → `has_updates: true`.

### Branch refs (e.g., main)

Un ref que matchea un nombre de branch (main, master, etc.) es branch ref.

**Primary method — GitHub commits API:**
```bash
gh api repos/{owner}/{repo}/commits/{branch} --jq '{sha: .sha, date: .commit.committer.date, message: .commit.message}'
```
Ejemplo para rocazul-bash-guard:
```bash
gh api repos/jvillar/claude-plugins/commits/main --jq '{sha: .sha, date: .commit.committer.date, message: .commit.message}'
```

**Fallback — git ls-remote:**
```bash
git ls-remote https://github.com/{owner}/{repo}.git refs/heads/{branch}
```
Devuelve el commit SHA actual del tip del branch.

**¿Hay updates?** Comparar `commit` SHA actual contra latest SHA. Si difieren y el campo `commit` no está vacío → `has_updates: true`. Si está vacío, registrar el latest SHA pero tratar como "unknown — necesita baseline commit grabado".

### Subpath repos

Cuando `path` no está vacío (ej. `"path": "plugins/bash-guard"`), no hay release por subdirectorio. Comprobar el commit a nivel repo y anotar el subpath:

```bash
gh api repos/jvillar/claude-plugins/commits/main --jq '{sha: .sha, date: .commit.committer.date}'
```

Para encontrar commits que tocaron específicamente el subpath (más preciso):
```bash
gh api "repos/jvillar/claude-plugins/commits?path=plugins/bash-guard&sha=main&per_page=1" --jq '.[0] | {sha: .sha, date: .commit.committer.date, message: .commit.message}'
```

### Multi-origin plugins

Comprobar cada origin del array `origins` independientemente, usando el método apropiado a su tipo de `ref`. Cada origin tiene su propio repo, path y ref — tratar como checks separados.

---

## Quick Summary Format

Tras escanear todos los plugins y comprobar upstreams, producir una tabla:

```
Estado de updates — 2026-05-26
═══════════════════════════════════════════════════════════════════════
Plugin                       Upstream                     Current      Latest     Status
──────────────────────────── ──────────────────────────── ──────────── ────────── ──────
rocazul-bash-guard           jvillar/claude-plugins       58e27a3      58e27a3    ✓
rocazul-security-shield      dmedina-dev/dev-forge        14f138d      14f138d    ✓
rocazul-on-this-day          —                            —            —          ⊘ (native)
═══════════════════════════════════════════════════════════════════════
✓ 2 up to date   ⊘ 1 skipped
```

**Status icons:**
- `⚡` — updates disponibles
- `✓` — al día
- `⊘` — skipped (nativo o sin customizations.json)

Tras la tabla, listar los plugins con updates con resúmenes de una línea:
```
⚡ rocazul-bash-guard: 58e27a3 → abc1234 — "3 commits desde el último fetch"
   ⚠ 1 conflicto potencial (scripts/bash-guard.py — modificado en custom-03)
```

---

## Detailed View Per Plugin

Cuando el usuario pida detalle de un plugin concreto o de todos los que tienen updates, producir vista detallada.

### Format

```
rocazul-bash-guard
  Origin:   jvillar/claude-plugins @ main (fetched 2026-05-26)
  Latest:   abc1234 (2026-06-10)
  Commits since current: 3

  abc1234 (2026-06-10): Ampliada lista SAFE_COMMANDS
    Files changed: scripts/bash-guard.py
    ⚠ scripts/bash-guard.py — conflicto con custom-03 (modified: añadidos comandos seguros propios)

  def5678 (2026-06-12): Bump del modelo de Haiku
    Files changed: scripts/bash-guard-llm.py
    ✓ scripts/bash-guard-llm.py — sin conflictos
```

### Conflict analysis rules

Para cada archivo cambiado upstream, cross-reference contra `customizations[]` locales:

- **customization `modified` o `renamed` + mismo archivo cambiado upstream** → `⚠` conflicto potencial. Mostrar: `⚠ {file} — conflicto con {id} ({summary})`
- **customization `removed` + mismo archivo o parent dir cambiado upstream** → `⚠` flag. Mostrar: `⚠ {file} — lo eliminaste (reason de la customization)`
- **customization `excluded` + cambios significativos en dir excluido upstream** → `⚠` flag. Mostrar: `⚠ {dir} — excluido (reason), pero upstream lo cambió significativamente`
- **customization `added` + archivo cambiado upstream** → no conflicto (adiciones locales no chocan). Mostrar: `✓ adición local — sin conflicto upstream`
- **Sin customization que matchee** → `✓` limpio. Mostrar: `✓ {file} — sin conflictos`

> **Importante:** `renamed` (extensión rocazul) se trata exactamente como `modified` para el análisis de conflictos. Si renombraste un archivo (típicamente `plugin.json`) y upstream lo modificó, hay conflicto.

"Cambio significativo" para dirs excluidos: si las release notes upstream mencionan el área excluida explícitamente, o si más de 3 archivos cambiaron dentro.

### Fetching changed files for a release

Lista de archivos cambiados en una release específica (tag-based):
```bash
gh api repos/{owner}/{repo}/compare/{old_tag}...{new_tag} --jq '.files[].filename'
```

Para branch-based, comparar commit SHAs:
```bash
gh api repos/{owner}/{repo}/compare/{old_sha}...{new_sha} --jq '.files[].filename'
```

Cuando el subpath no está vacío, filtrar archivos a sólo los dentro del subpath:
```bash
gh api "repos/jvillar/claude-plugins/compare/{old_sha}...{new_sha}" \
  --jq '.files[].filename | select(startswith("plugins/bash-guard/"))'
```

**Alternativa local (cuando `.upstream/` existe):** Si el upstream clone ya está cacheado de un apply previo, usar git localmente en vez del GitHub API — más rápido y sin rate limits:
```bash
git -C .upstream/{slug}/ diff --name-only {old-ref}..{new-ref} -- {subpath}
```

---

## Apply Update Flow

Cuando el usuario confirma que quiere aplicar un update a un plugin, seguir estos 7 pasos.

Los upstream clones se guardan persistentemente en `.upstream/` (gitignored). Un clone completo por upstream repo, compartido entre todos los plugins de ese repo. Primera ejecución clona, siguientes hacen fetch. Clones completos habilitan `git diff` entre cualquier par de refs para detección precisa de cambios.

### Repo slug convention

Derivar el directorio de clone del nombre del repo: reemplazar `/` por `-`.
- `jvillar/claude-plugins` → `.upstream/jvillar-claude-plugins/`
- `dmedina-dev/dev-forge` → `.upstream/dmedina-dev-dev-forge/`

### Step 1 — Asegurar upstream clone

```bash
SLUG=$(echo "{repo}" | tr '/' '-')

# Primera vez: full clone
if [ ! -d ".upstream/$SLUG" ]; then
  git clone "https://github.com/{repo}.git" ".upstream/$SLUG"
fi

# Siguientes: fetch latest
git -C ".upstream/$SLUG" fetch --all --tags

# Checkout del ref objetivo (tag o branch)
git -C ".upstream/$SLUG" checkout {target-ref}

# Para branch refs, fast-forward al último:
git -C ".upstream/$SLUG" pull 2>/dev/null || true
```

Path fuente: `.upstream/{slug}/{origin.path}/` (path vacío = repo root).

Ejemplo para rocazul-bash-guard:
```bash
git -C .upstream/jvillar-claude-plugins/ fetch --all --tags
git -C .upstream/jvillar-claude-plugins/ checkout main
# Source: .upstream/jvillar-claude-plugins/plugins/bash-guard/
```

### Step 2 — Identificar cambios upstream

Usar git para obtener la lista precisa de archivos cambiados upstream entre el old y el new ref.

**Cuando `origin.commit` está poblado (caso normal):**
```bash
git -C .upstream/{slug}/ diff --name-only {old-ref}..{new-ref} -- {subpath}
```

**Cuando `origin.commit` está vacío (primer sync):**
Skip diff — tratar todos los archivos upstream como nuevos. Copiar todo de `.upstream/` (aplicando filtros de customization en Step 3).

Para cada archivo cambiado, cross-reference contra `customizations[]`:

| File matches... | Action |
|-----------------|--------|
| target `excluded` | Skip — sigue excluido |
| target `removed` | Skip — sigue eliminado |
| target `modified` o `renamed` | Flag como **conflicto** — upstream cambió un archivo que tú también tocaste |
| Sin customization | **Cambio limpio** — aplicar directamente |

Para comprobar si upstream cambió un `modified`/`renamed` específico:
```bash
git -C .upstream/{slug}/ diff --quiet {old-ref}..{new-ref} -- {subpath}/{file}
# Exit 0 = sin cambio (seguro, keep local), Exit 1 = cambiado (conflicto)
```

### Step 3 — Aplicar cambios limpios

Para cada cambio limpio (sin customization que matchee):
- **Added/modified upstream** → copiar de `.upstream/{slug}/{subpath}/{file}` a `plugins/{name}/{file}`
- **Deleted upstream** → eliminar del local (confirmar con usuario antes de borrar)

**Nunca copiar:**
- Archivos/dirs que matcheen targets `excluded`
- Archivos/dirs que matcheen targets `removed`
- `.claude-plugin/customizations.json` (siempre preservar local)
- `.claude-plugin/plugin.json` (siempre preservar local — típicamente está `renamed` en rocazul)

Para primer sync (sin commit previo): copiar todos los archivos de `.upstream/{slug}/{subpath}/` a `plugins/{name}/`, filtrando targets excluded y removed.

### Step 4 — Manejar conflictos

Para cada archivo en conflicto (upstream cambió + customization local `modified`/`renamed`), mostrar el diff upstream junto con la versión local:

```
CONFLICT: scripts/bash-guard.py
  Customization: custom-03 — "Añadidos comandos seguros propios"
  Reason: "Ampliada SAFE_COMMANDS para incluir bq, gcloud, terraform"

  UPSTREAM DIFF ({old-ref}..{new-ref}):
  ─────────────────────────────────────
  [output of: git -C .upstream/{slug} diff {old}..{new} -- {path}]

  YOUR LOCAL VERSION:
  ─────────────────────────────────────
  [contenido local actual, secciones relevantes]

  Options:
    (k) keep local — preservar tu customization tal cual
    (u) use upstream — copiar de .upstream/ (elimina tu customization)
    (m) manual merge — aplicar upstream, luego re-aplicar tu customization a mano
```

Preguntar al usuario por cada conflicto antes de proceder.

### Step 5 — Reset option

Si el usuario quiere descartar todas las customizations y tomar upstream verbatim:
1. Eliminar todo en el directorio local del plugin (excepto `.claude-plugin/customizations.json` y `.claude-plugin/plugin.json`).
2. Copiar todos los archivos de `.upstream/{slug}/{subpath}/` (respetando origin path).
3. Limpiar `customizations[]` a un array vacío.
4. Actualizar campos de tracking en `origin` (ver Step 6).
5. Avisar al usuario: "Todas las customizations descartadas. Re-aplica los cambios necesarios a mano."

Hacerlo sólo si el usuario lo pide explícitamente.

### Step 6 — Update tracking

Obtener el SHA exacto del commit del clone:
```bash
git -C .upstream/{slug}/ rev-parse {target-ref}
```

Actualizar `customizations.json`:
```json
{
  "origin": {
    "ref": "{new-ref}",
    "commit": "{sha from rev-parse}",
    "fetched_at": "{today YYYY-MM-DD}"
  },
  "upstream_status": {
    "last_checked": "{today YYYY-MM-DD}",
    "latest_ref": "{new-ref}",
    "latest_commit": "{sha from rev-parse}",
    "has_updates": false,
    "summary": "",
    "changes": []
  }
}
```

Para conflictos donde el usuario eligió "keep local": dejar la entry de customization sin cambios.
Para conflictos donde el usuario eligió "use upstream": eliminar esa entry de `customizations[]`.

Validar el archivo tras editar:
```bash
python3 -m json.tool plugins/{name}/.claude-plugin/customizations.json
```

### Step 7 — Commit

No hace falta cleanup de directorio temporal — `.upstream/` persiste para futuros updates.

Stage los archivos del plugin cambiados y el customizations.json actualizado, luego commit:
```
feat({plugin-name}): update to {new-ref} from {old-ref}
```

---

## Multi-Origin Plugins

Para plugins que usen `origins` (array) en vez de `origin` (singular):

### Checking

Comprobar cada origin independientemente usando el método para su tipo de `ref`. Presentar resultados agrupados por plugin, con cada origin en su línea:

```
plugin-name (2 origins)
  owner/repo-a @ path-x (main)
    Latest commit: abc1234 (2026-06-10) — "summary"
    ⚡ Updates disponibles — 3 commits desde fetch
    ⚠ file.md — conflicto con custom-NN (modified)

  owner/repo-b @ path-y (main)
    Latest commit: def5678 (2026-06-12) — "summary"
    ✓ Al día
```

### Applying

Todos los origins del mismo repo comparten un único `.upstream/` clone. Fetch una vez, apply por origin.

Para cada origin en el array `origins`:
1. Asegurar `.upstream/{slug}/` clone (Step 1 — compartido, sólo fetch una vez por repo).
2. Identificar cambios para el subpath de este origin (Step 2).
3. Aplicar cambios limpios de `.upstream/{slug}/{origin.path}/` (Step 3).
4. Manejar conflictos para los archivos de este origin (Step 4).

Luego una vez para el plugin completo:
5. Manejar reset si se pide (Step 5).
6. Actualizar tracking para todos los origins (Step 6).
7. Commit (Step 7).

Entries de customization multi-origin tienen un campo `"origin"` (ej. `"origin": "path-x"`) que identifica a qué source aplican. Cross-referenciar una customization sólo contra cambios de su named origin, no todos.
